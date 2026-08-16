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
from sqlalchemy.orm import Mapped, mapped_column

class UserRole(str, PyEnum):
    CUSTOMER = "customer"
    SELLER = "seller"
    ADMIN = "admin"
class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(15), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        nullable=False)
    role: Mapped[UserRole] = mapped_column(
    SQLEnum(UserRole, name="userrole"),
    default=UserRole.CUSTOMER,
    nullable=False
)
  
    
class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(String(150), nullable=False)

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
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
    price : Mapped[float] = mapped_column(Numeric(10, 2),nullable=False)
    stock : Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    sku: Mapped[str] = mapped_column(
    String(100),
    unique=True,
    nullable=False)
    is_active : Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at : Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        nullable=False)
     
