from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.customer import Customer


class SellerApplicationStatus(str, PyEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class SellerApplication(Base):
    __tablename__ = "seller_applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id"), nullable=False, index=True
    )
    business_name: Mapped[str] = mapped_column(String(150), nullable=False)
    business_address: Mapped[str] = mapped_column(Text, nullable=False)
    tax_identifier: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[SellerApplicationStatus] = mapped_column(
        SQLEnum(SellerApplicationStatus, name="sellerapplicationstatus"),
        default=SellerApplicationStatus.PENDING,
        nullable=False,
        index=True,
    )
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    customer: Mapped["Customer"] = relationship(
        foreign_keys=[customer_id], back_populates="seller_applications"
    )
    reviewed_by: Mapped["Customer | None"] = relationship(
        foreign_keys=[reviewed_by_id]
    )
