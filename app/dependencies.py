
from collections.abc import AsyncIterator

from fastapi import Depends, HTTPException
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from jwt.exceptions import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jwt import decode_access_token
from app.database import AsyncSessionLocal
from app.models.customer import Customer, UserRole


security = HTTPBearer()


async def get_async_db() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as db:
        yield db


def _validate_token(credentials: HTTPAuthorizationCredentials) -> dict:
    try:
        return decode_access_token(credentials.credentials)
    except InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )


def _validate_customer_session(
    customer: Customer,
    payload: dict,
) -> None:
    token_iat = payload.get("iat")

    if (
        customer.password_changed_at is not None
        and token_iat is not None
        and token_iat < customer.password_changed_at.timestamp()
    ):
        raise HTTPException(
            status_code=401,
            detail="Session expired. Please log in again.",
        )


async def get_current_customer(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_async_db),
) -> Customer:
    payload = _validate_token(credentials)
    customer_id = payload.get("sub")

    if customer_id is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
        )

    try:
        customer_id = int(customer_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
        )

    result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = result.scalar_one_or_none()

    if customer is None:
        raise HTTPException(
            status_code=401,
            detail="Customer not found",
        )

    if not customer.is_active:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )

    _validate_customer_session(customer, payload)
    return customer


async def require_seller(
    customer: Customer = Depends(get_current_customer),
) -> Customer:
    if customer.role != UserRole.SELLER:
        raise HTTPException(
            status_code=403,
            detail="Seller access required",
        )
    return customer


async def require_admin(
    customer: Customer = Depends(get_current_customer),
) -> Customer:
    if customer.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )
    return customer


async def require_delivery_agent(
    customer: Customer = Depends(get_current_customer),
) -> Customer:
    if customer.role != UserRole.DELIVERY_AGENT:
        raise HTTPException(
            status_code=403,
            detail="Delivery agent access required",
        )
    return customer
