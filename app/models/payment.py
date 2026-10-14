from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PaymentStatus(str, PyEnum):
    CREATED = "created"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    FAILED = "failed"
    REFUNDED = "refunded"
    PENDING_COLLECTION = "pending_collection"
    COLLECTED = "collected"


class PaymentMethod(str, PyEnum):
    COD = "cod"
    RAZORPAY = "razorpay"


class Payment(Base):
    __tablename__ = "payments"

    __table_args__ = (
        CheckConstraint(
            "amount_paise > 0",
            name="ck_payments_amount_paise_positive",
        ),
        CheckConstraint(
            "amount_collected_paise IS NULL OR amount_collected_paise >= 0",
            name="ck_payments_amount_collected_nonnegative",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"),
        nullable=False,
        index=True,
    )

    amount_paise: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        default="INR",
        nullable=False,
    )

    status: Mapped[PaymentStatus] = mapped_column(
        SQLEnum(
            PaymentStatus,
            name="paymentstatus",
            values_callable=lambda enum_cls: [
                item.value for item in enum_cls
            ],
        ),
        default=PaymentStatus.CREATED,
        nullable=False,
    )

    payment_method: Mapped[PaymentMethod | None] = mapped_column(
        SQLEnum(PaymentMethod, name="paymentmethod", values_callable=lambda enum_cls: [item.value for item in enum_cls]),
        nullable=True,
    )

    amount_collected_paise: Mapped[int | None] = mapped_column(Integer, nullable=True)
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    collected_by_delivery_agent_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), nullable=True)

    gateway_order_id: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
        nullable=True,
    )

    gateway_payment_id: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
        nullable=True,
    )

    failure_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    order = relationship("Order")
