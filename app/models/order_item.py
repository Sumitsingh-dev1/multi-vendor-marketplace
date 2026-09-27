from typing import TYPE_CHECKING

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.order import OrderItemStatus

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.seller_product import SellerProduct
class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"),
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

    price: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )

    status: Mapped[OrderItemStatus] = mapped_column(
        SQLEnum(
            OrderItemStatus,
            name="orderitemstatus"
        ),
        default=OrderItemStatus.PENDING,
        nullable=False
    )
