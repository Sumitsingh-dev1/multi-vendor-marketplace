from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer, UserRole
from app.models.delivery_assignment import (
    DeliveryAssignment,
    DeliveryAssignmentStatus,
)
from app.models.order import Order, OrderItemStatus, OrderStatus
from app.models.order_item import OrderItem
from app.models.payment import Payment, PaymentMethod, PaymentStatus
from app.services.notification import notify


async def assign_delivery(
    db: AsyncSession,
    order_id: int,
    delivery_agent_id: int,
    admin_id: int,
):
    result = await db.execute(
        select(Order).where(Order.id == order_id).with_for_update()
    )
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found",
        )

    result = await db.execute(
        select(DeliveryAssignment).where(
            DeliveryAssignment.order_id == order_id,
            DeliveryAssignment.status.in_(
            {
                DeliveryAssignmentStatus.ASSIGNED,
                DeliveryAssignmentStatus.PICKED_UP,
                DeliveryAssignmentStatus.OUT_FOR_DELIVERY,
            }
            ),
        ).with_for_update()
    )
    active_assignment = result.scalar_one_or_none()

    if active_assignment is not None:
        raise HTTPException(
            status_code=400,
            detail="Order already has an active delivery assignment",
        )

    result = await db.execute(
        select(DeliveryAssignment).where(
            DeliveryAssignment.order_id == order_id,
            DeliveryAssignment.status
            == DeliveryAssignmentStatus.DELIVERED,
        )
    )
    delivered_assignment = result.scalar_one_or_none()

    if delivered_assignment is not None:
        raise HTTPException(
            status_code=400,
            detail="Order has already been delivered",
        )

    result = await db.execute(
        select(OrderItem).where(OrderItem.order_id == order_id).with_for_update()
    )
    order_items = result.scalars().all()

    if not order_items:
        raise HTTPException(
            status_code=400,
            detail="Order has no items",
        )

    active_items = [
        item
        for item in order_items
        if item.status != OrderItemStatus.CANCELLED
    ]

    if not active_items:
        raise HTTPException(
            status_code=400,
            detail="Order has no active items to deliver",
        )

    if not all(
        item.status == OrderItemStatus.SHIPPED
        for item in active_items
    ):
        raise HTTPException(
            status_code=400,
            detail="Order is not ready for delivery assignment",
        )

    payment = (await db.execute(
        select(Payment).where(Payment.order_id == order_id).with_for_update()
    )).scalar_one_or_none()
    if payment is None or payment.payment_method is None:
        raise HTTPException(status_code=409, detail="Order payment method is not eligible for delivery")
    if payment.payment_method == PaymentMethod.RAZORPAY and payment.status != PaymentStatus.CAPTURED:
        raise HTTPException(status_code=409, detail="Online payment must be captured before delivery assignment")

    result = await db.execute(
        select(Customer).where(
            Customer.id == delivery_agent_id,
            Customer.role == UserRole.DELIVERY_AGENT,
            Customer.is_active.is_(True),
        )
    )
    delivery_agent = result.scalar_one_or_none()

    if delivery_agent is None:
        raise HTTPException(
            status_code=404,
            detail="Delivery agent not found",
        )

    assignment = DeliveryAssignment(
        order_id=order_id,
        delivery_agent_id=delivery_agent_id,
        assigned_by=admin_id,
    )

    try:
        db.add(assignment)
        await db.flush()
        await notify(db, delivery_agent_id, "delivery_assigned", "Delivery assigned", "A delivery has been assigned to you.", "order", order_id, f"delivery:{assignment.id}:assigned:agent")
        await notify(db, order.customer_id, "delivery_assigned", "Delivery assigned", "A delivery agent has been assigned to your order.", "order", order_id, f"delivery:{assignment.id}:assigned:customer")
        await db.commit()
        await db.refresh(assignment)
    except Exception:
        await db.rollback()
        raise

    return assignment


async def list_my_deliveries(
    db: AsyncSession,
    delivery_agent_id: int,
):
    result = await db.execute(
        select(DeliveryAssignment).where(
            DeliveryAssignment.delivery_agent_id == delivery_agent_id
        ).with_for_update()
    )
    return result.scalars().all()


async def update_delivery_status(
    db: AsyncSession,
    order_id: int,
    delivery_agent_id: int,
    new_status: DeliveryAssignmentStatus,
):
    # Lock order, assignment, then payment in the same order as COD collection.
    order = (await db.execute(
        select(Order).where(Order.id == order_id).with_for_update()
    )).scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    result = await db.execute(
        select(DeliveryAssignment).where(
            DeliveryAssignment.order_id == order_id,
            DeliveryAssignment.delivery_agent_id == delivery_agent_id,
            DeliveryAssignment.status.in_(
            {
                DeliveryAssignmentStatus.ASSIGNED,
                DeliveryAssignmentStatus.PICKED_UP,
                DeliveryAssignmentStatus.OUT_FOR_DELIVERY,
            }
            ),
        ).with_for_update()
    )
    assignment = result.scalar_one_or_none()

    if assignment is None:
        raise HTTPException(
            status_code=404,
            detail="Delivery assignment not found",
        )

    allowed_transitions = {
        DeliveryAssignmentStatus.ASSIGNED: {
            DeliveryAssignmentStatus.PICKED_UP,
            DeliveryAssignmentStatus.CANCELLED,
        },
        DeliveryAssignmentStatus.PICKED_UP: {
            DeliveryAssignmentStatus.OUT_FOR_DELIVERY,
        },
        DeliveryAssignmentStatus.OUT_FOR_DELIVERY: {
            DeliveryAssignmentStatus.DELIVERED,
        },
        DeliveryAssignmentStatus.DELIVERED: set(),
        DeliveryAssignmentStatus.CANCELLED: set(),
    }

    if new_status not in allowed_transitions[assignment.status]:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Cannot change status from "
                f"'{assignment.status.value}' "
                f"to '{new_status.value}'"
            ),
        )

    assignment.status = new_status

    if new_status == DeliveryAssignmentStatus.OUT_FOR_DELIVERY:
        await notify(db, order.customer_id, "out_for_delivery", "Order out for delivery", "Your order is out for delivery.", "order", order_id, f"delivery:{assignment.id}:out_for_delivery:customer")

    if new_status == DeliveryAssignmentStatus.DELIVERED:
        payment = (await db.execute(
            select(Payment).where(Payment.order_id == order_id).with_for_update()
        )).scalar_one_or_none()
        if payment is None:
            await db.rollback()
            raise HTTPException(status_code=409, detail="Order has no payment record")
        if payment.payment_method is None:
            await db.rollback()
            raise HTTPException(status_code=409, detail="Order payment method is not eligible for delivery")
        if payment.payment_method == PaymentMethod.COD and payment.status != PaymentStatus.COLLECTED:
            await db.rollback()
            raise HTTPException(status_code=409, detail="COD payment must be collected before delivery completion")
        if payment.payment_method == PaymentMethod.RAZORPAY and payment.status != PaymentStatus.CAPTURED:
            await db.rollback()
            raise HTTPException(status_code=409, detail="Online payment must be captured before delivery completion")

        items = (await db.execute(
            select(OrderItem).where(OrderItem.order_id == order_id).with_for_update()
        )).scalars().all()
        active_items = [item for item in items if item.status != OrderItemStatus.CANCELLED]
        if not active_items or not all(item.status == OrderItemStatus.SHIPPED for item in active_items):
            await db.rollback()
            raise HTTPException(status_code=400, detail="Order items are not eligible for delivery completion")
        for item in active_items:
            item.status = OrderItemStatus.DELIVERED
        order.status = OrderStatus.DELIVERED
        await notify(db, order.customer_id, "order_delivered", "Order delivered", "Your order has been delivered.", "order", order_id, f"delivery:{assignment.id}:delivered:customer")

    await db.commit()
    await db.refresh(assignment)

    return assignment


async def cancel_delivery_assignment(
    db: AsyncSession,
    order_id: int,
):
    # Share the order lock used by customer cancellation so those operations
    # cannot produce contradictory order and delivery states.
    await db.execute(select(Order).where(Order.id == order_id).with_for_update())
    result = await db.execute(
        select(DeliveryAssignment).where(
            DeliveryAssignment.order_id == order_id,
            DeliveryAssignment.status.in_(
            {
                DeliveryAssignmentStatus.ASSIGNED,
                DeliveryAssignmentStatus.PICKED_UP,
                DeliveryAssignmentStatus.OUT_FOR_DELIVERY,
            }
            ),
        ).with_for_update()
    )
    assignment = result.scalar_one_or_none()

    if assignment is None:
        raise HTTPException(
            status_code=404,
            detail="Active delivery assignment not found",
        )

    assignment.status = DeliveryAssignmentStatus.CANCELLED

    await db.commit()
    await db.refresh(assignment)

    return assignment
