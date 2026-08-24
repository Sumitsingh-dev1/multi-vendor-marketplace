from fastapi import APIRouter, Depends,HTTPException,Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_seller
from app.models.customer import Customer, SellerProduct,Product
from app.schemas.customer import SellerProductResponse,SellerProductUpdate,MySellerProductResponse,MySellerProductListResponse

router = APIRouter(
    prefix="/seller-products",
    tags=["Seller Products"]
)


@router.get("/", response_model=list[SellerProductResponse])
def get_my_products(
    seller: Customer = Depends(require_seller),
    db: Session = Depends(get_db)
):
    statement = select(SellerProduct).where(
        SellerProduct.seller_id == seller.id
    )

    result = db.execute(statement)

    return result.scalars().all()
@router.patch("/{seller_product_id}")
def update_seller_product(
    seller_product_id: int,
    data: SellerProductUpdate,
    seller: Customer = Depends(require_seller),
    db: Session = Depends(get_db)
):
    statement = select(SellerProduct).where(
        SellerProduct.id == seller_product_id,
        SellerProduct.seller_id == seller.id
    )

    seller_product = db.execute(
        statement
    ).scalar_one_or_none()

    if seller_product is None:
        raise HTTPException(
            status_code=404,
            detail="Seller product not found"
        )

    if data.price is not None:
        seller_product.price = data.price

    if data.stock is not None:
        seller_product.stock = data.stock

    if data.sku is not None:
        seller_product.sku = data.sku

    if data.is_active is not None:
        seller_product.is_active = data.is_active

    db.commit()
    db.refresh(seller_product)

    return {
        "message": "Seller product updated successfully"
    }
@router.get("/", response_model=list[MySellerProductResponse])
def get_my_products(
    seller: Customer = Depends(require_seller),
    search: str | None = None,
    is_active: bool | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    statement = (
        select(SellerProduct, Product)
        .join(
            Product,
            Product.id == SellerProduct.product_id
        )
        .where(
            SellerProduct.seller_id == seller.id
        )
    )

    if search:
        statement = statement.where(
            Product.name.ilike(f"%{search}%")
        )

    if is_active is not None:
        statement = statement.where(
            SellerProduct.is_active == is_active
        )

    statement = statement.limit(limit).offset(offset)

    result = db.execute(statement)
    rows = result.all()

    responses = []

    for seller_product, product in rows:
        responses.append(
            MySellerProductResponse(
                seller_product_id=seller_product.id,
                product_id=product.id,
                name=product.name,
                price=float(seller_product.price),
                stock=seller_product.stock,
                sku=seller_product.sku,
                is_active=seller_product.is_active
            )
        )

    return responses
@router.get(
    "/",
    response_model=MySellerProductListResponse
)
def get_my_products(
    seller: Customer = Depends(require_seller),

    category_id: int | None = None,
    product_id: int | None = None,
    search: str | None = None,
    is_active: bool | None = None,

    sort: str = Query(
        default="newest"
    ),

    limit: int = Query(
        default=20,
        ge=1,
        le=100
    ),

    offset: int = Query(
        default=0,
        ge=0
    ),

    db: Session = Depends(get_db)
):
    # -----------------------------------
    # Base query
    # -----------------------------------

    statement = (
        select(SellerProduct, Product)
        .join(
            Product,
            Product.id == SellerProduct.product_id
        )
        .where(
            SellerProduct.seller_id == seller.id
        )
    )

    # -----------------------------------
    # Filter by category
    # -----------------------------------

    if category_id is not None:
        statement = statement.where(
            Product.category_id == category_id
        )

    # -----------------------------------
    # Filter by specific product
    # -----------------------------------

    if product_id is not None:
        statement = statement.where(
            SellerProduct.product_id == product_id
        )

    # -----------------------------------
    # Search by product name
    # -----------------------------------

    if search:
        statement = statement.where(
            Product.name.ilike(
                f"%{search}%"
            )
        )

    # -----------------------------------
    # Filter active/inactive
    # -----------------------------------

    if is_active is not None:
        statement = statement.where(
            SellerProduct.is_active == is_active
        )

    # -----------------------------------
    # Sorting
    # -----------------------------------

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

    # -----------------------------------
    # Pagination
    # Fetch one extra record
    # to calculate has_next
    # -----------------------------------

    statement = statement.limit(
        limit + 1
    ).offset(offset)

    # -----------------------------------
    # Execute query
    # -----------------------------------

    result = db.execute(statement)

    rows = result.all()

    # -----------------------------------
    # Check whether next page exists
    # -----------------------------------

    has_next = len(rows) > limit

    # Keep only requested number
    rows = rows[:limit]

    # -----------------------------------
    # Convert DB rows into response items
    # -----------------------------------

    items = []

    for seller_product, product in rows:
        items.append(
            MySellerProductResponse(
                seller_product_id=seller_product.id,
                product_id=product.id,
                name=product.name,
                price=float(seller_product.price),
                stock=seller_product.stock,
                sku=seller_product.sku,
                is_active=seller_product.is_active,
            )
        )

    # -----------------------------------
    # Final response
    # -----------------------------------

    return MySellerProductListResponse(
        items=items,
        limit=limit,
        offset=offset,
        has_next=has_next,
    )
@router.get(
    "/{seller_product_id}",
    response_model=MySellerProductResponse
)
def get_my_seller_product(
    seller_product_id: int,
    seller: Customer = Depends(require_seller),
    db: Session = Depends(get_db)
):
    statement = (
        select(SellerProduct, Product)
        .join(
            Product,
            Product.id == SellerProduct.product_id
        )
        .where(
            SellerProduct.id == seller_product_id,
            SellerProduct.seller_id == seller.id
        )
    )

    result = db.execute(statement).first()

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Seller product not found"
        )

    seller_product, product = result

    return MySellerProductResponse(
        seller_product_id=seller_product.id,
        product_id=product.id,
        name=product.name,
        price=float(seller_product.price),
        stock=seller_product.stock,
        sku=seller_product.sku,
        is_active=seller_product.is_active
    )