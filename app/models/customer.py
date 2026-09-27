from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING

from app.database import Base

from sqlalchemy import (
    String,
    Boolean,
    Text,
    ForeignKey,
    Enum as SQLEnum,
    DateTime
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.address import Address

if TYPE_CHECKING:
    from app.models.cart import Cart
    from app.models.delivery_assignment import DeliveryAssignment
    from app.models.password_reset_token import PasswordResetToken
    from app.models.seller_product import SellerProduct

class UserRole(str, PyEnum):
    CUSTOMER = "customer"
    SELLER = "seller"
    ADMIN = "admin"
    DELIVERY_AGENT = "delivery_agent"


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    phone: Mapped[str] = mapped_column(
        String(15),
        nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        nullable=False
    )

    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, name="userrole"),
        default=UserRole.CUSTOMER,
        nullable=False
    )

    seller_listings: Mapped[list["SellerProduct"]] = relationship(
        back_populates="seller"
    )

    cart: Mapped["Cart | None"] = relationship(
        back_populates="customer",
        uselist=False
    )
    addresses: Mapped[list["Address"]] = relationship(
    back_populates="customer",
    cascade="all, delete-orphan"
)
    delivery_assignments = relationship(
    "DeliveryAssignment",
    foreign_keys="DeliveryAssignment.delivery_agent_id",
    back_populates="delivery_agent"
)

    assigned_delivery_assignments = relationship(
      "DeliveryAssignment",
      foreign_keys="DeliveryAssignment.assigned_by",
       back_populates="assigned_by_admin"
)
    password_changed_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True),
    nullable=True
)
    password_reset_tokens: Mapped[list["PasswordResetToken"]] = relationship(
    back_populates="customer",
    cascade="all, delete-orphan"
    )