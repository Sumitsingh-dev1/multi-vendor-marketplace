from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.delivery_assignment import DeliveryAssignmentStatus


class DeliveryAssignmentCreate(BaseModel):
    delivery_agent_id: int


class DeliveryAssignmentResponse(BaseModel):
    id: int
    order_id: int
    delivery_agent_id: int
    assigned_by: int
    status: DeliveryAssignmentStatus
    assigned_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeliveryStatusUpdate(BaseModel):
    status: DeliveryAssignmentStatus