from typing import TYPE_CHECKING
from app.database import Base

from sqlalchemy import (
    String,
    ForeignKey
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship
)
if TYPE_CHECKING:
    from app.models.customer import Customer


class SellerServiceArea(Base):
    __tablename__ = "seller_service_areas"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    seller_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id"),
        nullable=False
    )

    postal_code: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )

    seller: Mapped["Customer"] = relationship()