from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.customer import Customer
from app.models.product import Product
from app.models.seller_product import SellerProduct


def create_product_listing(
    db: Session,
    seller: Customer,
    name: str,
    description: str | None,
    category_id: int,
    price: float,
    stock: int,
    sku: str,
):
    category = db.execute(
        select(Category).where(
            Category.id == category_id,
            Category.is_active.is_(True),
        )
    ).scalar_one_or_none()

    if category is None:
        return None

    product = Product(
        name=name,
        description=description,
        category_id=category_id,
    )

    db.add(product)
    db.flush()

    seller_product = SellerProduct(
        seller_id=seller.id,
        product_id=product.id,
        price=price,
        stock=stock,
        sku=sku,
    )

    db.add(seller_product)
    db.commit()

    return seller_product


def get_products(
    db: Session,
    category_id: int | None = None,
    search: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    sort: str | None = None,
    limit: int = 20,
    offset: int = 0,
):
    statement = (
        select(Product, SellerProduct)
        .join(
            SellerProduct,
            SellerProduct.product_id == Product.id,
        )
        .where(
            SellerProduct.is_active.is_(True),
            SellerProduct.stock > 0,
        )
    )

    if category_id is not None:
        statement = statement.where(
            Product.category_id == category_id
        )

    if search:
        statement = statement.where(
            Product.name.ilike(f"%{search}%")
        )

    if min_price is not None:
        statement = statement.where(
            SellerProduct.price >= min_price
        )

    if max_price is not None:
        statement = statement.where(
            SellerProduct.price <= max_price
        )

    if sort == "price_asc":
        statement = statement.order_by(
            SellerProduct.price.asc()
        )
    elif sort == "price_desc":
        statement = statement.order_by(
            SellerProduct.price.desc()
        )
    elif sort == "newest":
        statement = statement.order_by(
            SellerProduct.created_at.desc()
        )

    statement = statement.limit(limit + 1).offset(offset)

    rows = db.execute(statement).all()

    has_next = len(rows) > limit

    return rows[:limit], has_next