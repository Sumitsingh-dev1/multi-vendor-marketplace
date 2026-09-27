from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.seller_product import SellerProduct


def list_seller_products(
    db: Session,
    seller_id: int,
    category_id: int | None = None,
    product_id: int | None = None,
    search: str | None = None,
    is_active: bool | None = None,
    sort: str = "newest",
    limit: int = 20,
    offset: int = 0,
):
    statement = (
        select(SellerProduct, Product)
        .join(
            Product,
            Product.id == SellerProduct.product_id,
        )
        .where(
            SellerProduct.seller_id == seller_id
        )
    )

    if category_id is not None:
        statement = statement.where(
            Product.category_id == category_id
        )

    if product_id is not None:
        statement = statement.where(
            SellerProduct.product_id == product_id
        )

    if search:
        statement = statement.where(
            Product.name.ilike(f"%{search}%")
        )

    if is_active is not None:
        statement = statement.where(
            SellerProduct.is_active == is_active
        )

    if sort == "newest":
        statement = statement.order_by(
            SellerProduct.created_at.desc()
        )
    elif sort == "oldest":
        statement = statement.order_by(
            SellerProduct.created_at.asc()
        )
    elif sort == "price_asc":
        statement = statement.order_by(
            SellerProduct.price.asc()
        )
    elif sort == "price_desc":
        statement = statement.order_by(
            SellerProduct.price.desc()
        )

    statement = statement.limit(
        limit + 1
    ).offset(offset)

    rows = db.execute(statement).all()

    has_next = len(rows) > limit

    return rows[:limit], has_next


def get_seller_product(
    db: Session,
    seller_id: int,
    seller_product_id: int,
):
    statement = (
        select(SellerProduct, Product)
        .join(
            Product,
            Product.id == SellerProduct.product_id,
        )
        .where(
            SellerProduct.id == seller_product_id,
            SellerProduct.seller_id == seller_id,
        )
    )

    return db.execute(statement).first()


def update_seller_product(
    db: Session,
    seller_id: int,
    seller_product_id: int,
    price: float | None = None,
    stock: int | None = None,
    sku: str | None = None,
    is_active: bool | None = None,
):
    statement = select(SellerProduct).where(
        SellerProduct.id == seller_product_id,
        SellerProduct.seller_id == seller_id,
    )

    seller_product = db.execute(
        statement
    ).scalar_one_or_none()

    if seller_product is None:
        return None

    if price is not None:
        seller_product.price = price

    if stock is not None:
        seller_product.stock = stock

    if sku is not None:
        seller_product.sku = sku

    if is_active is not None:
        seller_product.is_active = is_active

    db.commit()
    db.refresh(seller_product)

    return seller_product