from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

TicketCategory = Literal["order", "payment", "delivery", "product", "account", "return_refund", "other"]
TicketStatus = Literal["open", "in_progress", "waiting_for_user", "resolved", "closed"]
TicketPriority = Literal["low", "normal", "high", "urgent"]


class TicketCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject: str = Field(min_length=1, max_length=200)
    category: TicketCategory
    message: str = Field(min_length=1, max_length=5000)
    order_id: int | None = Field(default=None, gt=0)
    @field_validator("subject", "message")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Text must not be blank")
        return value


class TicketMessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    body: str = Field(min_length=1, max_length=5000)
    @field_validator("body")
    @classmethod
    def reject_blank_body(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message must not be blank")
        return value


class TicketAdminUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    assigned_admin_id: int | None = Field(default=None, gt=0)


class TicketDisplayCustomer(BaseModel):
    id: int
    name: str


class TicketResponse(BaseModel):
    id: int
    public_reference: str
    subject: str
    category: str
    status: str
    priority: str
    order_id: int | None
    creator: TicketDisplayCustomer
    assigned_admin: TicketDisplayCustomer | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    closed_at: datetime | None


class TicketListResponse(BaseModel):
    items: list[TicketResponse]
    limit: int
    offset: int
    has_next: bool


class TicketMessageResponse(BaseModel):
    id: int
    ticket_id: int
    author: TicketDisplayCustomer
    body: str
    created_at: datetime


class TicketMessageListResponse(BaseModel):
    items: list[TicketMessageResponse]
    limit: int
    offset: int
    has_next: bool
