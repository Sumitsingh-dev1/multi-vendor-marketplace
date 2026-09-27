from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING
from app.database import Base

from sqlalchemy import (
    String,
    Numeric,
    Integer,
    ForeignKey,
    Enum as SQLEnum,
    Float
)

from sqlalchemy.orm import Mapped, mapped_column,relationship
if TYPE_CHECKING:
    from app.models.delivery_assignment import DeliveryAssignment

class OrderStatus(str, PyEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class OrderItemStatus(str, PyEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id"),
        nullable=False
    )

    delivery_address_line: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    delivery_city: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    delivery_state: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    delivery_postal_code: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )

    delivery_latitude: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    delivery_longitude: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    status: Mapped[OrderStatus] = mapped_column(
        SQLEnum(OrderStatus, name="orderstatus"),
        default=OrderStatus.PENDING,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        nullable=False
    )
    delivery_assignments: Mapped[
        list["DeliveryAssignment"]
        ] = relationship(
         back_populates="order"
)
    
    
    