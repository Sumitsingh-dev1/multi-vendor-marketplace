"""Focused PostgreSQL-backed authorization regression tests."""

import os
import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.engine import make_url
from app.core.config import settings
from app.core.jwt import create_access_token
from app.database import AsyncSessionLocal, async_engine
from app.main import app
from app.models.customer import Customer, UserRole


RUN_DB_INTEGRATION_TESTS = (
    os.getenv("RUN_DB_INTEGRATION_TESTS") == "1"
)

pytestmark = pytest.mark.skipif(
    not RUN_DB_INTEGRATION_TESTS,
    reason="Set RUN_DB_INTEGRATION_TESTS=1 to run database integration tests",
)

if RUN_DB_INTEGRATION_TESTS:
    database_name = make_url(settings.DATABASE_URL).database
    if database_name != "marketplace_test":
        raise RuntimeError(
            "Authorization integration tests may only run against "
            "'marketplace_test'."
        )


@pytest_asyncio.fixture(autouse=True, loop_scope="function")
async def dispose_async_engine_after_test():
    yield
    await async_engine.dispose()


@pytest_asyncio.fixture(loop_scope="function")
async def customer_context():
    suffix = uuid.uuid4().hex

    customer = Customer(
        name="Authorization Test Customer",
        email=f"auth-customer-{suffix}@example.test",
        password_hash="not-used-by-this-test",
        phone="5550101999",
        role=UserRole.CUSTOMER,
        is_active=True,
    )

    async with AsyncSessionLocal() as db:
        db.add(customer)
        await db.commit()
        await db.refresh(customer)
        customer_id = customer.id

    token = create_access_token({"sub": str(customer_id)})
    client = AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    )

    try:
        yield {
            "client": client,
            "headers": {"Authorization": f"Bearer {token}"},
        }
    finally:
        await client.aclose()

        async with AsyncSessionLocal() as db:
            await db.execute(
                delete(Customer).where(Customer.id == customer_id)
            )
            await db.commit()


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("GET", "/seller-products/", None),
        ("POST", "/payments/orders/1/collect-cod", {"amount_collected_paise": 1}),
        ("GET", "/categories/admin", None),
        (
            "POST",
            "/categories/",
            {
                "name": "Authorization Test Category",
                "description": "Must not be created by a customer",
            },
        ),
        (
            "POST",
            "/admin/delivery-agents",
            {
                "name": "Unauthorized Test Agent",
                "email": "unauthorized-agent@example.test",
                "phone": "5550101998",
                "password": "Test-Password-123!",
            },
        ),
    ],
)
@pytest.mark.asyncio(loop_scope="function")
async def test_customer_cannot_access_role_protected_routes(
    customer_context,
    method,
    path,
    payload,
):
    client = customer_context["client"]
    headers = customer_context["headers"]

    if payload is None:
        response = await client.request(
            method, path, headers=headers
        )
    else:
        response = await client.request(
            method, path, headers=headers, json=payload
        )

    assert response.status_code == 403, (
        f"{method} {path} should deny ordinary customers; "
        f"received {response.status_code}: {response.text}"
    )
