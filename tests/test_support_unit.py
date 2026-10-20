"""Database-free support-ticket contract tests."""

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.schemas.support import (
    TicketAdminUpdate,
    TicketCreate,
    TicketMessageCreate,
)
from app.services.support import (
    ADMIN_TRANSITIONS,
    ensure_ticket_replyable,
)


def test_ticket_create_rejects_administrative_fields() -> None:
    with pytest.raises(ValidationError):
        TicketCreate.model_validate(
            {
                "subject": "Need help",
                "category": "order",
                "message": "Details",
                "status": "closed",
            }
        )


def test_ticket_create_accepts_only_known_categories() -> None:
    with pytest.raises(ValidationError):
        TicketCreate(
            subject="Need help",
            category="made_up",
            message="Details",
        )


def test_admin_update_rejects_unsupported_fields() -> None:
    with pytest.raises(ValidationError):
        TicketAdminUpdate.model_validate(
            {"creator_customer_id": 10}
        )


def test_ticket_lifecycle_does_not_reopen_from_admin_update() -> None:
    assert ADMIN_TRANSITIONS["closed"] == set()
    assert "open" not in ADMIN_TRANSITIONS["resolved"]
    assert "in_progress" in ADMIN_TRANSITIONS["open"]


@pytest.mark.parametrize(
    "payload",
    [
        {"subject": "   ", "category": "order", "message": "Need help"},
        {"subject": "Need help", "category": "order", "message": "  \n "},
    ],
)
def test_ticket_create_rejects_blank_text(payload: dict) -> None:
    with pytest.raises(ValidationError):
        TicketCreate.model_validate(payload)


def test_ticket_message_rejects_blank_body() -> None:
    with pytest.raises(ValidationError):
        TicketMessageCreate(body="   \n ")


def test_ticket_create_trims_valid_text() -> None:
    ticket = TicketCreate(
        subject="  Need help  ",
        category="order",
        message="  Order has not arrived.  ",
    )

    assert ticket.subject == "Need help"
    assert ticket.message == "Order has not arrived."


@pytest.mark.parametrize("status", ["resolved", "closed"])
def test_replies_require_reopening_resolved_or_closed_tickets(
    status: str,
) -> None:
    with pytest.raises(HTTPException) as exc_info:
        ensure_ticket_replyable(status)

    assert exc_info.value.status_code == 409


@pytest.mark.parametrize(
    "status",
    ["open", "in_progress", "waiting_for_user"],
)
def test_replies_allowed_for_active_tickets(status: str) -> None:
    ensure_ticket_replyable(status)