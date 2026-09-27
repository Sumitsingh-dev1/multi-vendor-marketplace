from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.dependencies import (
    get_db,
    require_admin,
    require_delivery_agent,
)
from app.models.customer import Customer
from app.schemas.delivery_assignment import (
    DeliveryAssignmentCreate,
    DeliveryAssignmentResponse,
    DeliveryStatusUpdate,
)
from app.services.delivery_assignment import (
    assign_delivery,
    list_my_deliveries,
    update_delivery_status,
)


router = APIRouter(
    prefix="/orders",
    tags=["Delivery Assignment"],
)


@router.post(
    "/{order_id}/assign-delivery",
    response_model=DeliveryAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
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


@router.get(
    "/my-deliveries",
    response_model=list[DeliveryAssignmentResponse],
)
def get_my_deliveries(
    db: Session = Depends(get_db),
    current_delivery_agent: Customer = Depends(
        require_delivery_agent
    ),
):
    return list_my_deliveries(
        db=db,
        delivery_agent_id=current_delivery_agent.id,
    )


@router.patch(
    "/{order_id}/delivery-status",
    response_model=DeliveryAssignmentResponse,
)
def update_delivery_status_route(
    order_id: int,
    data: DeliveryStatusUpdate,
    db: Session = Depends(get_db),
    current_delivery_agent: Customer = Depends(
        require_delivery_agent
    ),
):
    return update_delivery_status(
        db=db,
        order_id=order_id,
        delivery_agent_id=current_delivery_agent.id,
        new_status=data.status,
    )