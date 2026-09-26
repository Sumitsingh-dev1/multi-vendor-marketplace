from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.customer import Customer, UserRole
from app.models.delivery_assignment import DeliveryAssignment
from app.models.order import Order


def assign_delivery(
    db: Session,
    order_id: int,
    delivery_agent_id: int,
    admin_id: int,
):
    order = db.query(Order).filter(
        Order.id == order_id
    ).first()

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    delivery_agent = db.query(Customer).filter(
        Customer.id == delivery_agent_id,
        Customer.role == UserRole.DELIVERY_AGENT
    ).first()

    if not delivery_agent:
        raise HTTPException(
            status_code=404,
            detail="Delivery agent not found"
        )

    if order.delivery_assignment:
        raise HTTPException(
            status_code=400,
            detail="Order already has a delivery assignment"
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