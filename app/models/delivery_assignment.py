from datetime import datetime
from enum import Enum as PyEnum

from app.database import Base

from sqlalchemy import (
    String,
    ForeignKey,
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.order import Order

    
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
    order: Mapped["Order"] = relationship(
    back_populates="delivery_assignments"
)
    delivery_agent: Mapped["Customer"] = relationship(
    foreign_keys=[delivery_agent_id],
    back_populates="delivery_assignments"
)

    assigned_by_admin: Mapped["Customer"] = relationship(
    foreign_keys=[assigned_by],
    back_populates="assigned_delivery_assignments"
)