from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.database import async_engine
from app.dependencies import get_async_db, get_current_customer

from app.schemas.customer import CustomerCreate, LoginRequest

from app.models.customer import Customer, UserRole

from app.core.security import hash_password, verify_password
from app.core.jwt import create_access_token
from app.core.config import settings

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
from app.api.routes.seller_applications import router as seller_applications_router
from app.api.routes.admin import router as admin_router
from app.api.routes.payment import router as payment_router
from app.api.routes.review import router as review_router
from app.api.routes.notification import router as notification_router

from datetime import datetime, timezone

from pathlib import Path

from fastapi.staticfiles import StaticFiles


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        yield
    finally:
        await async_engine.dispose()


app = FastAPI(
    title="Multi-Vendor Marketplace API",
    version="1.0.0",
    lifespan=lifespan,
)
UPLOADS_DIR = Path("uploads")
UPLOADS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

app.mount(
    "/uploads",
    StaticFiles(directory="uploads"),
    name="uploads",
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
app.include_router(seller_applications_router)
app.include_router(admin_router)
app.include_router(payment_router)
app.include_router(review_router)
app.include_router(notification_router)

# =========================================================
# HOME
# =========================================================

@app.get("/")
async def home():
    return {
        "message": "Marketplace API is running"
    }


# =========================================================
# DATABASE TEST
# =========================================================

if settings.ENABLE_DB_TEST_ENDPOINT:
    @app.get("/db-test", include_in_schema=False)
    async def db_test(db: AsyncSession = Depends(get_async_db)):
        await db.execute(text("SELECT 1"))
        return {"database_connected": True}


# =========================================================
# CREATE CUSTOMER
# =========================================================
@app.post("/customers")
async def create_customer(
    data: CustomerCreate,
    db: AsyncSession = Depends(get_async_db),
):
    customer = Customer(
        name=data.name,
        email=data.email,
        password_hash=await run_in_threadpool(
            hash_password,
            data.password,
        ),
        phone=data.phone,
        role=UserRole.CUSTOMER,
    )

    try:
        db.add(customer)
        await db.commit()
        await db.refresh(customer)

    except IntegrityError:
        await db.rollback()

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
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_async_db),
):
    statement = select(Customer).where(
        Customer.email == data.email
    )

    result = await db.execute(
        statement
    )
    customer = result.scalar_one_or_none()

    if customer is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    password_ok = await run_in_threadpool(
        verify_password,
        data.password,
        customer.password_hash
    )

    if not password_ok or not customer.is_active:
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
async def get_my_profile(
    customer: Customer = Depends(get_current_customer)
):
    return {
    "id": customer.id,
    "name": customer.name,
    "email": customer.email,
    "phone": customer.phone,
    "role": customer.role
}
