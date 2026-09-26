from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import text, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import engine
from app.dependencies import get_db, get_current_customer

from app.schemas.customer import CustomerCreate, LoginRequest

from app.models.customer import Customer, UserRole

from app.core.security import hash_password, verify_password
from app.core.jwt import create_access_token

from app.api.routes.product import router as products_router
from app.api.routes.categories import router as categories_router
from app.api.routes.seller_products import router as seller_products_router
from app.api.routes.Cart import router as cart_router
from app.api.routes.order import router as Orders
from app.api.routes import seller_service_area
from app.api.routes.address import router as addresses
from app.api.routes.delivery_assignment import (
    router as delivery_assignment_router
)
from app.api.routes.password_reset import router as password_reset_router

from datetime import datetime, timezone
app = FastAPI(
    title="Multi-Vendor Marketplace API",
    version="1.0.0"
)


# =========================================================
# ROUTERS
# =========================================================

app.include_router(products_router)
app.include_router(categories_router)
app.include_router(seller_products_router)
app.include_router(cart_router)
app.include_router(Orders)
app.include_router(seller_service_area.router)
app.include_router(addresses)
app.include_router(delivery_assignment_router)
app.include_router(password_reset_router)

# =========================================================
# HOME
# =========================================================

@app.get("/")
def home():
    return {
        "message": "Marketplace API is running"
    }


# =========================================================
# DATABASE TEST
# =========================================================

@app.get("/db-test")
def db_test():
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT current_database(), current_schema()")
        )

        row = result.fetchone()

    return {
        "database": row[0],
        "schema": row[1]
    }


# =========================================================
# CREATE CUSTOMER
# =========================================================
@app.post("/customers")
def create_customer(
    data: CustomerCreate,
    db: Session = Depends(get_db)
):
    if data.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Admin accounts cannot be created through public registration"
        )

    customer = Customer(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        phone=data.phone,
        role=data.role
    )

    try:
        db.add(customer)
        db.commit()
        db.refresh(customer)

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Email already registered"
        )

    return {
        "message": "Customer registered successfully",
        "id": customer.id,
        "role": customer.role
    }

# =========================================================
# LOGIN
# =========================================================

@app.post("/login")
def login(
    data: LoginRequest,
    db: Session = Depends(get_db)
):
    statement = select(Customer).where(
        Customer.email == data.email
    )

    customer = db.execute(
        statement
    ).scalar_one_or_none()

    if customer is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if not verify_password(
        data.password,
        customer.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    token = create_access_token({
        "sub": str(customer.id)
    })

    return {
        "access_token": token,
        "token_type": "bearer"
    }


# =========================================================
# CURRENT CUSTOMER PROFILE
# =========================================================

@app.get("/customers/me")
def get_my_profile(
    customer: Customer = Depends(get_current_customer)
):
    return {
    "id": customer.id,
    "name": customer.name,
    "email": customer.email,
    "phone": customer.phone,
    "role": customer.role
}