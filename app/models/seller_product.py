from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.cart_item import CartItem
    from app.models.customer import Customer
    from app.models.product import Product


class SellerProduct(Base):
    __tablename__ = "seller_products"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    seller_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id"),
        nullable=False
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
        nullable=False
    )

    price: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )

    stock: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    sku: Mapped[str] = mapped_column(
        String(100),
        unique=True,
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

    seller: Mapped["Customer"] = relationship(
        back_populates="seller_listings"
    )

    product: Mapped["Product"] = relationship(
        back_populates="seller_listings"
    )

    cart_items: Mapped[list["CartItem"]] = relationship(
        back_populates="seller_product"
    )