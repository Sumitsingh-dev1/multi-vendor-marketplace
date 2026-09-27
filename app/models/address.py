from typing import TYPE_CHECKING
from sqlalchemy import (
    String,
    Float,
    ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column,relationship
from app.database import Base

if TYPE_CHECKING:
    from app.models.customer import Customer

class Address(Base):
    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id"),
        nullable=False
    )

    label: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )

    latitude: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    longitude: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    address_line: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    city: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    state: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    postal_code: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )
    customer: Mapped["Customer"] = relationship(
    back_populates="addresses"
)