from datetime import datetime
from enum import Enum as PyEnum

from app.database import Base

from sqlalchemy import (
    String,
    Boolean,
    Text,
    Numeric,
    Integer,
    ForeignKey,
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.order import  OrderItemStatus

class UserRole(str, PyEnum):
    CUSTOMER = "customer"
    SELLER = "seller"
    ADMIN = "admin"


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


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id"),
        nullable=False
    )

    seller_listings: Mapped[list["SellerProduct"]] = relationship(
        back_populates="product"
    )

    category: Mapped["Category"] = relationship(
        back_populates="products"
    )

class SellerProduct(Base):
    __tablename__ = "seller_products"

    id: Mapped[int] = mapped_column(primary_key=True)

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
   


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    products: Mapped[list["Product"]] = relationship(
        back_populates="category"
    )


class Cart(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id"),
        nullable=False,
        unique=True
    )

    customer: Mapped["Customer"] = relationship(
        back_populates="cart"
    )

    items: Mapped[list["CartItem"]] = relationship(
        back_populates="cart",
        cascade="all, delete-orphan"
    )


class CartItem(Base):
    __tablename__ = "cart_items"

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