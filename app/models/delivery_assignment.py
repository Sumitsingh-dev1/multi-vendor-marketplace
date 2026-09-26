from datetime import datetime
from enum import Enum as PyEnum

from app.database import Base

from sqlalchemy import (
    String,
    ForeignKey,
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

class DeliveryAssignmentStatus(str, PyEnum):
    ASSIGNED = "assigned"
    PICKED_UP = "picked_up"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
class DeliveryAssignment(Base):
    __tablename__ = "delivery_assignments"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"),
        unique=True,
        nullable=False
    )

    delivery_agent_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id"),
        nullable=False
    )

    assigned_by: Mapped[int] = mapped_column(
        ForeignKey("customers.id"),
        nullable=False
    )

    status: Mapped[DeliveryAssignmentStatus] = mapped_column(
        SQLEnum(
            DeliveryAssignmentStatus,
            name="deliveryassignmentstatus"
        ),
        default=DeliveryAssignmentStatus.ASSIGNED,
        nullable=False
    )

    assigned_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        nullable=False
    )

    order = relationship(
        "Order",
        back_populates="delivery_assignment"
    )

    delivery_agent = relationship(
        "Customer",
        foreign_keys=[delivery_agent_id],
        back_populates="delivery_assignments"
    )

    assigned_by_admin = relationship(
        "Customer",
        foreign_keys=[assigned_by],
        back_populates="assigned_delivery_assignments"
    )