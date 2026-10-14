from datetime import datetime
from pydantic import BaseModel, Field
from app.models.payment import PaymentMethod, PaymentStatus


class CodCollectionRequest(BaseModel):
    amount_collected_paise: int = Field(gt=0)


class PaymentResponse(BaseModel):
    payment_id: int
    order_id: int
    payment_method: PaymentMethod | None
    payment_status: PaymentStatus
    amount_due_paise: int
    amount_collected_paise: int | None
    collected_at: datetime | None
