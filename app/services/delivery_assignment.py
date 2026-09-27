from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.customer import Customer, UserRole
from app.models.delivery_assignment import (
    DeliveryAssignment,
    DeliveryAssignmentStatus,
)
from app.models.order import Order, OrderItemStatus, OrderStatus
from app.models.order_item import OrderItem


def assign_delivery(
    db: Session,
    order_id: int,
    delivery_agent_id: int,
    admin_id: int,
):
    order = db.query(Order).filter(
        Order.id == order_id
    ).first()

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found",
        )

    active_assignment = db.query(
        DeliveryAssignment
    ).filter(
        DeliveryAssignment.order_id == order_id,
        DeliveryAssignment.status.in_(
            {
                DeliveryAssignmentStatus.ASSIGNED,
                DeliveryAssignmentStatus.PICKED_UP,
                DeliveryAssignmentStatus.OUT_FOR_DELIVERY,
            }
        ),
    ).first()

    if active_assignment is not None:
        raise HTTPException(
            status_code=400,
            detail="Order already has an active delivery assignment",
        )

    delivered_assignment = db.query(
        DeliveryAssignment
    ).filter(
        DeliveryAssignment.order_id == order_id,
        DeliveryAssignment.status
        == DeliveryAssignmentStatus.DELIVERED,
    ).first()

    if delivered_assignment is not None:
        raise HTTPException(
            status_code=400,
            detail="Order has already been delivered",
        )

    order_items = db.query(OrderItem).filter(
        OrderItem.order_id == order_id
    ).all()

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

    delivery_agent = db.query(Customer).filter(
        Customer.id == delivery_agent_id,
        Customer.role == UserRole.DELIVERY_AGENT,
    ).first()

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
        db.commit()
        db.refresh(assignment)
    except Exception:
        db.rollback()
        raise

    return assignment


def list_my_deliveries(
    db: Session,
    delivery_agent_id: int,
):
    return db.query(DeliveryAssignment).filter(
        DeliveryAssignment.delivery_agent_id == delivery_agent_id
    ).all()


def update_delivery_status(
    db: Session,
    order_id: int,
    delivery_agent_id: int,
    new_status: DeliveryAssignmentStatus,
):
    assignment = db.query(DeliveryAssignment).filter(
        DeliveryAssignment.order_id == order_id,
        DeliveryAssignment.delivery_agent_id == delivery_agent_id,
        DeliveryAssignment.status.in_(
            {
                DeliveryAssignmentStatus.ASSIGNED,
                DeliveryAssignmentStatus.PICKED_UP,
                DeliveryAssignmentStatus.OUT_FOR_DELIVERY,
            }
        ),
    ).first()

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

    if new_status == DeliveryAssignmentStatus.DELIVERED:
        order = db.query(Order).filter(
            Order.id == order_id
        ).first()

        if order is None:
            db.rollback()

            raise HTTPException(
                status_code=404,
                detail="Order not found",
            )

        order.status = OrderStatus.DELIVERED

    db.commit()
    db.refresh(assignment)

    return assignment


def cancel_delivery_assignment(
    db: Session,
    order_id: int,
):
    assignment = db.query(
        DeliveryAssignment
    ).filter(
        DeliveryAssignment.order_id == order_id,
        DeliveryAssignment.status.in_(
            {
                DeliveryAssignmentStatus.ASSIGNED,
                DeliveryAssignmentStatus.PICKED_UP,
                DeliveryAssignmentStatus.OUT_FOR_DELIVERY,
            }
        ),
    ).first()

    if assignment is None:
        raise HTTPException(
            status_code=404,
            detail="Active delivery assignment not found",
        )

    assignment.status = DeliveryAssignmentStatus.CANCELLED

    db.commit()
    db.refresh(assignment)

    return assignment