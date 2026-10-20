"""PostgreSQL-backed support API integration tests.

These tests are opt-in and must run only against marketplace_test.
Set RUN_DB_INTEGRATION_TESTS=1 to enable them.
"""

import os
import uuid
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import and_, delete, or_, select
from sqlalchemy.engine import make_url
from app.database import AsyncSessionLocal, async_engine

@pytest_asyncio.fixture(autouse=True, loop_scope="function")
async def dispose_async_engine_after_test():
    yield
    await async_engine.dispose()

RUN_DB_INTEGRATION_TESTS = (
    os.getenv("RUN_DB_INTEGRATION_TESTS") == "1"
)

pytestmark = pytest.mark.skipif(
    not RUN_DB_INTEGRATION_TESTS,
    reason="Set RUN_DB_INTEGRATION_TESTS=1 to run database integration tests",
)

from app.core.config import settings

if RUN_DB_INTEGRATION_TESTS:
    database_name = make_url(settings.DATABASE_URL).database
    if database_name != "marketplace_test":
        raise RuntimeError(
            "Support integration tests are permitted only against "
            "'marketplace_test'. The configured database name is "
            f"{database_name!r}."
        )

from app.core.jwt import create_access_token
from app.main import app
from app.models.customer import Customer, UserRole
from app.models.notification import Notification
from app.models.support import SupportMessage, SupportTicket



@pytest_asyncio.fixture(loop_scope="function")
async def support_api_context() -> Any:
    suffix = uuid.uuid4().hex

    customer = Customer(
        name="Integration Customer",
        email=f"support-customer-{suffix}@example.test",
        password_hash="not-used-by-this-test",
        phone="5550101001",
        role=UserRole.CUSTOMER,
        is_active=True,
    )
    other_customer = Customer(
        name="Other Integration Customer",
        email=f"support-other-{suffix}@example.test",
        password_hash="not-used-by-this-test",
        phone="5550101002",
        role=UserRole.CUSTOMER,
        is_active=True,
    )
    admin = Customer(
        name="Integration Admin",
        email=f"support-admin-{suffix}@example.test",
        password_hash="not-used-by-this-test",
        phone="5550101003",
        role=UserRole.ADMIN,
        is_active=True,
    )

    async with AsyncSessionLocal() as db:
        db.add_all([customer, other_customer, admin])
        await db.commit()

        await db.refresh(customer)
        await db.refresh(other_customer)
        await db.refresh(admin)

        customer_id = customer.id
        other_customer_id = other_customer.id
        admin_id = admin.id

    customer_token = create_access_token({"sub": str(customer_id)})
    other_customer_token = create_access_token(
        {"sub": str(other_customer_id)}
    )
    admin_token = create_access_token({"sub": str(admin_id)})

    client = AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    )

    try:
        yield {
            "client": client,
            "customer_id": customer_id,
            "other_customer_id": other_customer_id,
            "admin_id": admin_id,
            "customer_headers": {
                "Authorization": f"Bearer {customer_token}"
            },
            "other_customer_headers": {
                "Authorization": f"Bearer {other_customer_token}"
            },
            "admin_headers": {
                "Authorization": f"Bearer {admin_token}"
            },
        }
    finally:
        await client.aclose()

        customer_ids = [
            customer_id,
            other_customer_id,
            admin_id,
        ]

        async with AsyncSessionLocal() as db:
            ticket_ids = (
                await db.execute(
                    select(SupportTicket.id).where(
                        or_(
                            SupportTicket.creator_customer_id.in_(
                                customer_ids
                            ),
                            SupportTicket.assigned_admin_id.in_(
                                customer_ids
                            ),
                        )
                    )
                )
            ).scalars().all()

            cleanup_ticket_ids = ticket_ids or [-1]

            # Remove dependent rows before deleting customers and tickets.
            await db.execute(
                delete(SupportMessage).where(
                    or_(
                        SupportMessage.author_customer_id.in_(
                            customer_ids
                        ),
                        SupportMessage.ticket_id.in_(
                            cleanup_ticket_ids
                        ),
                    )
                )
            )

            await db.execute(
                delete(Notification).where(
                    or_(
                        Notification.recipient_customer_id.in_(
                            customer_ids
                        ),
                        and_(
                            Notification.resource_type == "support_ticket",
                            Notification.resource_id.in_(
                                cleanup_ticket_ids
                            ),
                        ),
                    )
                )
            )

            await db.execute(
                delete(SupportTicket).where(
                    or_(
                        SupportTicket.creator_customer_id.in_(
                            customer_ids
                        ),
                        SupportTicket.assigned_admin_id.in_(
                            customer_ids
                        ),
                    )
                )
            )

            await db.execute(
                delete(Customer).where(
                    Customer.id.in_(customer_ids)
                )
            )

            await db.commit()


async def create_test_ticket(
    context: dict[str, Any],
) -> dict[str, Any]:
    response = await context["client"].post(
        "/support/tickets",
        headers=context["customer_headers"],
        json={
            "subject": "Integration test ticket",
            "category": "account",
            "message": "This ticket was created by an integration test.",
        },
    )

    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_create_ticket_persists_message_and_notifies_admin(
    support_api_context: dict[str, Any],
) -> None:
    context = support_api_context
    ticket = await create_test_ticket(context)
    ticket_id = ticket["id"]

    assert ticket["status"] == "open"
    assert ticket["creator"]["id"] == context["customer_id"]

    response = await context["client"].get(
        f"/support/tickets/{ticket_id}/messages",
        headers=context["customer_headers"],
    )

    assert response.status_code == 200, response.text
    messages = response.json()["items"]
    assert len(messages) == 1
    assert messages[0]["body"] == (
        "This ticket was created by an integration test."
    )

    async with AsyncSessionLocal() as db:
        notification = (
            await db.execute(
                select(Notification).where(
                    Notification.recipient_customer_id
                    == context["admin_id"],
                    Notification.resource_type == "support_ticket",
                    Notification.resource_id == ticket_id,
                    Notification.notification_type
                    == "support_ticket_created",
                )
            )
        ).scalar_one_or_none()

    assert notification is not None


@pytest.mark.asyncio
async def test_customer_cannot_access_another_customers_ticket(
    support_api_context: dict[str, Any],
) -> None:
    context = support_api_context
    ticket = await create_test_ticket(context)
    ticket_id = ticket["id"]
    client = context["client"]
    outsider_headers = context["other_customer_headers"]

    detail = await client.get(
        f"/support/tickets/{ticket_id}",
        headers=outsider_headers,
    )
    messages = await client.get(
        f"/support/tickets/{ticket_id}/messages",
        headers=outsider_headers,
    )
    reply = await client.post(
        f"/support/tickets/{ticket_id}/messages",
        headers=outsider_headers,
        json={"body": "Trying to access somebody else's ticket."},
    )

    assert detail.status_code == 404
    assert messages.status_code == 404
    assert reply.status_code == 404

    admin_list = await client.get(
        "/admin/support/tickets",
        headers=outsider_headers,
    )
    assert admin_list.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_update_ticket_and_invalid_assignment_is_rejected(
    support_api_context: dict[str, Any],
) -> None:
    context = support_api_context
    ticket = await create_test_ticket(context)
    ticket_id = ticket["id"]
    client = context["client"]

    update = await client.patch(
        f"/admin/support/tickets/{ticket_id}",
        headers=context["admin_headers"],
        json={
            "status": "in_progress",
            "priority": "high",
            "assigned_admin_id": context["admin_id"],
        },
    )

    assert update.status_code == 200, update.text
    updated_ticket = update.json()
    assert updated_ticket["status"] == "in_progress"
    assert updated_ticket["priority"] == "high"
    assert updated_ticket["assigned_admin"]["id"] == (
        context["admin_id"]
    )

    invalid_assignment = await client.patch(
        f"/admin/support/tickets/{ticket_id}",
        headers=context["admin_headers"],
        json={
            "assigned_admin_id": context["customer_id"],
        },
    )

    assert invalid_assignment.status_code == 422

    async with AsyncSessionLocal() as db:
        notification = (
            await db.execute(
                select(Notification).where(
                    Notification.recipient_customer_id
                    == context["customer_id"],
                    Notification.resource_type == "support_ticket",
                    Notification.resource_id == ticket_id,
                    Notification.notification_type
                    == "support_ticket_updated",
                )
            )
        ).scalar_one_or_none()

    assert notification is not None


@pytest.mark.asyncio
async def test_resolved_ticket_must_be_reopened_before_reply(
    support_api_context: dict[str, Any],
) -> None:
    context = support_api_context
    ticket = await create_test_ticket(context)
    ticket_id = ticket["id"]
    client = context["client"]

    resolve = await client.patch(
        f"/admin/support/tickets/{ticket_id}",
        headers=context["admin_headers"],
        json={"status": "resolved"},
    )
    assert resolve.status_code == 200, resolve.text

    blocked_reply = await client.post(
        f"/support/tickets/{ticket_id}/messages",
        headers=context["customer_headers"],
        json={"body": "This reply should be blocked while resolved."},
    )
    assert blocked_reply.status_code == 409

    reopen = await client.post(
        f"/support/tickets/{ticket_id}/reopen",
        headers=context["customer_headers"],
    )
    assert reopen.status_code == 200, reopen.text
    assert reopen.json()["status"] == "open"

    allowed_reply = await client.post(
        f"/support/tickets/{ticket_id}/messages",
        headers=context["customer_headers"],
        json={"body": "This reply should succeed after reopening."},
    )
    assert allowed_reply.status_code == 201, allowed_reply.text
    assert allowed_reply.json()["body"] == (
        "This reply should succeed after reopening."
    )