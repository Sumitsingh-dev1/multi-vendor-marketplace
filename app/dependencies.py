from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select

from app.database import SessionLocal
from app.models.customer import Customer, UserRole
from app.core.jwt import decode_access_token
from jwt.exceptions import InvalidTokenError


security = HTTPBearer()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_customer(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db=Depends(get_db)
):
    token = credentials.credentials

    try:
        payload = decode_access_token(token)
    except InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    customer_id = payload.get("sub")

    if customer_id is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

    statement = select(Customer).where(
        Customer.id == int(customer_id)
    )

    customer = db.execute(statement).scalar_one_or_none()

    if customer is None:
        raise HTTPException(
            status_code=401,
            detail="Customer not found"
        )

    return customer


def require_seller(
    customer: Customer = Depends(get_current_customer)
):
    if customer.role != UserRole.SELLER:
        raise HTTPException(
            status_code=403,
            detail="Seller access required"
        )

    return customer
def require_admin(
    customer: Customer = Depends(get_current_customer)
):
    if customer.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    return customer