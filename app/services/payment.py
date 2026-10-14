
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
from typing import Any

import razorpay
from fastapi import HTTPException
from razorpay.errors import SignatureVerificationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.models.customer import Customer, UserRole
from app.models.delivery_assignment import DeliveryAssignment, DeliveryAssignmentStatus
from app.models.order import Order, OrderItemStatus, OrderStatus
from app.models.order_item import OrderItem
from app.models.payment import Payment, PaymentMethod, PaymentStatus
from app.services.notification import notify


def get_razorpay_client() -> razorpay.Client:
    """Create a Razorpay client using server-side configuration."""
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Payment gateway is not configured",
        )

    return razorpay.Client(
        auth=(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET,
        )
    )


def payment_checkout_details(payment: Payment) -> dict[str, Any]:
    """Return the details the frontend needs to open Razorpay Checkout."""
    return {
        "payment_id": payment.id,
        "order_id": payment.order_id,
        "gateway_order_id": payment.gateway_order_id,
        "amount": payment.amount_paise,
        "currency": payment.currency,
        "key_id": settings.RAZORPAY_KEY_ID,
        "status": payment.status.value,
        "payment_method": payment.payment_method.value if payment.payment_method else None,
        "amount_collected_paise": payment.amount_collected_paise,
        "collected_at": payment.collected_at,
    }


async def create_payment_order(
    db: AsyncSession,
    customer_id: int,
    order_id: int,
) -> dict[str, Any]:
    """Create a Razorpay order for an order owned by this customer."""
    raise HTTPException(
        status_code=503,
        detail="Online payments are unavailable until Razorpay is configured and verified",
    )
    client = get_razorpay_client()

    result = await db.execute(
        select(Order).where(
            Order.id == order_id,
            Order.customer_id == customer_id,
        )
    )
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found",
        )

    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=409,
            detail="Payment can only be initiated for a pending order",
        )

    result = await db.execute(
        select(OrderItem)
        .where(OrderItem.order_id == order.id)
        .order_by(OrderItem.id)
    )
    order_items = result.scalars().all()

    active_items = [
        item
        for item in order_items
        if item.status != OrderItemStatus.CANCELLED
    ]

    if not active_items:
        raise HTTPException(
            status_code=400,
            detail="Order has no active items to pay for",
        )

    # Use the prices saved in the order, not prices from the request.
    total_rupees = sum(
        (
            Decimal(str(item.price)) * item.quantity
            for item in active_items
        ),
        start=Decimal("0.00"),
    )

    amount_paise = int(
        (total_rupees * 100).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP,
        )
    )

    if amount_paise <= 0:
        raise HTTPException(
            status_code=400,
            detail="Order amount must be greater than zero",
        )

    # Prevent creating a second active payment attempt unnecessarily.
    result = await db.execute(
        select(Payment)
        .where(Payment.order_id == order.id)
        .order_by(Payment.id.desc())
    )
    existing_payments = result.scalars().all()

    if any(
        payment.status == PaymentStatus.CAPTURED
        for payment in existing_payments
    ):
        raise HTTPException(
            status_code=409,
            detail="This order has already been paid",
        )

    for existing in existing_payments:
        if (
            existing.status in {
                PaymentStatus.CREATED,
                PaymentStatus.AUTHORIZED,
            }
            and existing.gateway_order_id
        ):
            if existing.amount_paise != amount_paise:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "An existing payment attempt has a different "
                        "amount. Please contact support."
                    ),
                )

            return payment_checkout_details(existing)

    # Save a local payment record before calling the gateway.
    payment = Payment(
        order_id=order.id,
        amount_paise=amount_paise,
        currency="INR",
        status=PaymentStatus.CREATED,
        payment_method=PaymentMethod.RAZORPAY,
    )

    db.add(payment)
    await db.commit()
    await db.refresh(payment)

    gateway_request = {
        "amount": amount_paise,
        "currency": payment.currency,
        "receipt": f"mktp{payment.id}o{order.id}",
        "notes": {
            "marketplace_order_id": str(order.id),
            "payment_record_id": str(payment.id),
        },
    }

    try:
        # Razorpay's SDK uses synchronous HTTP requests.
        # Run it in a thread so it doesn't block the async event loop.
        gateway_order = await run_in_threadpool(
            client.order.create,
            data=gateway_request,
        )
    except Exception as exc:
        payment.status = PaymentStatus.FAILED
        payment.failure_reason = (
            f"Gateway order creation failed ({type(exc).__name__})"
        )[:500]
        await db.commit()

        raise HTTPException(
            status_code=502,
            detail="Payment gateway could not create an order",
        ) from exc

    gateway_order_id = (
        gateway_order.get("id")
        if isinstance(gateway_order, dict)
        else None
    )

    try:
        response_amount = int(gateway_order.get("amount"))
    except (AttributeError, TypeError, ValueError):
        response_amount = None

    if (
        not gateway_order_id
        or response_amount != amount_paise
        or gateway_order.get("currency") != payment.currency
    ):
        payment.status = PaymentStatus.FAILED
        payment.failure_reason = (
            "Gateway returned an invalid order response"
        )
        await db.commit()

        raise HTTPException(
            status_code=502,
            detail="Invalid payment gateway response",
        )

    payment.gateway_order_id = gateway_order_id
    await db.commit()
    await db.refresh(payment)

    return payment_checkout_details(payment)


async def verify_payment(
    db: AsyncSession,
    customer_id: int,
    payment_record_id: int,
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
) -> Payment:
    """Verify a checkout signature and confirm the gateway's payment state."""
    client = get_razorpay_client()

    if not all(
        value and value.strip()
        for value in (
            razorpay_order_id,
            razorpay_payment_id,
            razorpay_signature,
        )
    ):
        raise HTTPException(
            status_code=400,
            detail="Payment verification fields are required",
        )

    # Ensure this payment belongs to an order owned by the customer.
    result = await db.execute(
        select(Payment)
        .join(Order, Payment.order_id == Order.id)
        .where(
            Payment.id == payment_record_id,
            Order.customer_id == customer_id,
        )
    )
    payment = result.scalar_one_or_none()

    if payment is None:
        raise HTTPException(
            status_code=404,
            detail="Payment record not found",
        )

    if payment.gateway_order_id != razorpay_order_id:
        raise HTTPException(
            status_code=400,
            detail="Payment order does not match our records",
        )

    # Verify the signature using Razorpay's official SDK.
    signature_data = {
        "razorpay_order_id": razorpay_order_id,
        "razorpay_payment_id": razorpay_payment_id,
        "razorpay_signature": razorpay_signature,
    }

    try:
        await run_in_threadpool(
            client.utility.verify_payment_signature,
            signature_data,
        )
    except SignatureVerificationError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid payment signature",
        ) from exc

    # A valid signature alone is not proof that funds were captured.
    try:
        gateway_payment = await run_in_threadpool(
            client.payment.fetch,
            razorpay_payment_id,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Could not verify payment status with the gateway",
        ) from exc

    if not isinstance(gateway_payment, dict):
        raise HTTPException(
            status_code=502,
            detail="Invalid payment gateway response",
        )

    try:
        gateway_amount = int(gateway_payment.get("amount"))
    except (TypeError, ValueError):
        gateway_amount = None

    if (
        gateway_payment.get("order_id") != payment.gateway_order_id
        or gateway_amount != payment.amount_paise
        or gateway_payment.get("currency") != payment.currency
    ):
        raise HTTPException(
            status_code=400,
            detail="Gateway payment details do not match our records",
        )

    # Make retries idempotent for the same captured payment.
    if payment.status == PaymentStatus.CAPTURED:
        if payment.gateway_payment_id == razorpay_payment_id:
            return payment

        raise HTTPException(
            status_code=409,
            detail="This payment record has already been captured",
        )

    if payment.gateway_payment_id not in (
        None,
        razorpay_payment_id,
    ):
        raise HTTPException(
            status_code=409,
            detail="A different gateway payment is already recorded",
        )

    gateway_status = gateway_payment.get("status")

    if gateway_status == "captured":
        payment.status = PaymentStatus.CAPTURED
        payment.failure_reason = None

    elif gateway_status == "authorized":
        payment.status = PaymentStatus.AUTHORIZED

    elif gateway_status == "failed":
        payment.status = PaymentStatus.FAILED
        payment.failure_reason = str(
            gateway_payment.get("error_description")
            or "Gateway reported a failed payment"
        )[:500]

    else:
        raise HTTPException(
            status_code=409,
            detail="Payment has not been captured",
        )

    payment.gateway_payment_id = razorpay_payment_id

    await db.commit()
    await db.refresh(payment)

    return payment


async def collect_cod_payment(
    db: AsyncSession,
    order_id: int,
    delivery_agent: Customer,
    amount_collected_paise: int,
) -> Payment:
    """Record full COD collection before delivery can be completed."""
    if delivery_agent.role != UserRole.DELIVERY_AGENT or not delivery_agent.is_active:
        raise HTTPException(status_code=403, detail="Active delivery-agent access required")
    try:
        order = (await db.execute(select(Order).where(Order.id == order_id).with_for_update())).scalar_one_or_none()
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        assignment = (await db.execute(select(DeliveryAssignment).where(
            DeliveryAssignment.order_id == order_id,
            DeliveryAssignment.delivery_agent_id == delivery_agent.id,
        ).with_for_update())).scalar_one_or_none()
        if assignment is None:
            raise HTTPException(status_code=403, detail="You are not assigned to this delivery")
        if assignment.status != DeliveryAssignmentStatus.OUT_FOR_DELIVERY or order.status != OrderStatus.SHIPPED:
            raise HTTPException(status_code=409, detail="COD collection requires an out-for-delivery shipped order")
        payment = (await db.execute(select(Payment).where(Payment.order_id == order_id).with_for_update())).scalar_one_or_none()
        if payment is None:
            raise HTTPException(status_code=404, detail="Payment record not found")
        if payment.payment_method != PaymentMethod.COD:
            raise HTTPException(status_code=409, detail="This order is not a COD order")
        if payment.status != PaymentStatus.PENDING_COLLECTION:
            raise HTTPException(status_code=409, detail="COD payment has already been settled or is not collectable")
        if amount_collected_paise != payment.amount_paise:
            raise HTTPException(status_code=400, detail="Collected amount must equal the full outstanding amount")
        payment.status = PaymentStatus.COLLECTED
        payment.amount_collected_paise = amount_collected_paise
        payment.collected_by_delivery_agent_id = delivery_agent.id
        payment.collected_at = datetime.now(timezone.utc)
        await notify(db, order.customer_id, "cod_collected", "COD payment collected", "Cash on delivery collection was recorded for your order.", "order", order_id, f"payment:{payment.id}:cod_collected:customer")
        await db.commit()
        await db.refresh(payment)
        return payment
    except Exception:
        await db.rollback()
        raise
