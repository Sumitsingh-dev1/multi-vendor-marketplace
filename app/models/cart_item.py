from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.cart import Cart
    from app.models.seller_product import SellerProduct


class CartItem(Base):
    __tablename__ = "cart_items"
    __table_args__ = (
        UniqueConstraint("cart_id", "seller_product_id", name="uq_cart_items_cart_seller_product"),
        CheckConstraint("quantity > 0", name="ck_cart_items_quantity_positive"),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    cart_id: Mapped[int] = mapped_column(
        ForeignKey("carts.id"),
        nullable=False
    )

    seller_product_id: Mapped[int] = mapped_column(
        ForeignKey("seller_products.id"),
        nullable=False
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    cart: Mapped["Cart"] = relationship(
        back_populates="items"
    )

    seller_product: Mapped["SellerProduct"] = relationship(
        back_populates="cart_items"
    )
