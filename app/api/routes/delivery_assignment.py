from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_admin
from app.models.customer import Customer
from app.schemas.delivery_assignment import (
    DeliveryAssignmentCreate,
    DeliveryAssignmentResponse,
)
from app.services.delivery_assignment import assign_delivery


router = APIRouter(
    prefix="/orders",
    tags=["Delivery Assignment"]
)


@router.post(
    "/{order_id}/assign-delivery",
    response_model=DeliveryAssignmentResponse,
    status_code=status.HTTP_201_CREATED
)
def assign_delivery_to_order(
    order_id: int,
    data: DeliveryAssignmentCreate,
    db: Session = Depends(get_db),
    current_admin: Customer = Depends(require_admin),
):
    assignment = assign_delivery(
        db=db,
        order_id=order_id,
        delivery_agent_id=data.delivery_agent_id,
        admin_id=current_admin.id,
    )

    return assignment