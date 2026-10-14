from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_async_db, require_delivery_agent
from app.models.customer import Customer
from app.schemas.payment import CodCollectionRequest, PaymentResponse
from app.services.payment import collect_cod_payment

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/orders/{order_id}/collect-cod", response_model=PaymentResponse)
async def collect_cod(
    order_id: int,
    data: CodCollectionRequest,
    delivery_agent: Customer = Depends(require_delivery_agent),
    db: AsyncSession = Depends(get_async_db),
):
    payment = await collect_cod_payment(
        db=db,
        order_id=order_id,
        delivery_agent=delivery_agent,
        amount_collected_paise=data.amount_collected_paise,
    )
    return PaymentResponse(
        payment_id=payment.id,
        order_id=payment.order_id,
        payment_method=payment.payment_method,
        payment_status=payment.status,
        amount_due_paise=payment.amount_paise,
        amount_collected_paise=payment.amount_collected_paise,
        collected_at=payment.collected_at,
    )
