from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SupportTicketStatus(str, PyEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_FOR_USER = "waiting_for_user"
    RESOLVED = "resolved"
    CLOSED = "closed"


class SupportTicketPriority(str, PyEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class SupportTicket(Base):
    __tablename__ = "support_tickets"
    __table_args__ = (
        CheckConstraint("category IN ('order', 'payment', 'delivery', 'product', 'account', 'return_refund', 'other')", name="ck_support_tickets_category"),
        CheckConstraint("status IN ('open', 'in_progress', 'waiting_for_user', 'resolved', 'closed')", name="ck_support_tickets_status"),
        CheckConstraint("priority IN ('low', 'normal', 'high', 'urgent')", name="ck_support_tickets_priority"),
        Index("ix_support_tickets_creator_updated", "creator_customer_id", "updated_at", "id"),
        Index("ix_support_tickets_admin_filters", "status", "priority", "category", "updated_at", "id"),
        Index("ix_support_tickets_order_id", "order_id"),
        Index("ix_support_tickets_assigned_admin_id", "assigned_admin_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    public_reference: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    creator_customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default=SupportTicketStatus.OPEN.value, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default=SupportTicketPriority.NORMAL.value, nullable=False)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True)
    assigned_admin_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SupportMessage(Base):
    __tablename__ = "support_messages"
    __table_args__ = (Index("ix_support_messages_ticket_created", "ticket_id", "created_at", "id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("support_tickets.id"), nullable=False)
    author_customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
