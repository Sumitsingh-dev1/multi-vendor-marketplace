from fastapi import APIRouter, Depends,HTTPException,Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.dependencies import get_db, require_seller
from app.models.customer import Category,Product,Customer,SellerProduct
from app.schemas.customer import SellerProductResponse,SellerListingCreate,ProductListingResponse,ProductListResponse


router = APIRouter(
    prefix="/products",
    tags=["Product"]
)


@router.post("/")
def create_product(
    data: SellerListingCreate,
    seller: Customer = Depends(require_seller),
    db: Session = Depends(get_db)
):
    try:
        category = db.execute(
        select(Category).where(
        Category.id == data.category_id,
        Category.is_active.is_(True)
           )
        ).scalar_one_or_none()
        

        if category is None:
            raise HTTPException(
                status_code=404,
                detail="Category not found"
            )

        product = Product(
            name=data.name,
            description=data.description,
            category_id=data.category_id
        )

        db.add(product)
        db.flush()

        seller_product = SellerProduct(
            seller_id=seller.id,
            product_id=product.id,
            price=data.price,
            stock=data.stock,
            sku=data.sku
        )

        db.add(seller_product)
        db.commit()

        return {
            "message": "Product listed successfully"
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not create product"
        )
@router.get("/", response_model=ProductListResponse)
def get_products(
    category_id: int | None = None,
    search: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    sort: str | None = None,

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
    # Base query:
    # Product + SellerProduct
    statement = (
        select(Product, SellerProduct)
        .join(
            SellerProduct,
            SellerProduct.product_id == Product.id
        )
        .where(
            SellerProduct.is_active.is_(True),
            SellerProduct.stock > 0
        )
    )

    # -------------------------
    # Category filter
    # -------------------------
    if category_id is not None:
        statement = statement.where(
            Product.category_id == category_id
        )

    # -------------------------
    # Search by product name
    # -------------------------
    if search:
        statement = statement.where(
            Product.name.ilike(f"%{search}%")
        )

    # -------------------------
    # Minimum price
    # -------------------------
    if min_price is not None:
        statement = statement.where(
            SellerProduct.price >= min_price
        )

    # -------------------------
    # Maximum price
    # -------------------------
    if max_price is not None:
        statement = statement.where(
            SellerProduct.price <= max_price
        )

    # -------------------------
    # Sorting
    # -------------------------
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

    # -------------------------
    # Pagination
    # Fetch one extra row so
    # we can determine has_next
    # -------------------------
    statement = statement.limit(limit + 1).offset(offset)

    # Execute ONE database query
    result = db.execute(statement)

    rows = result.all()

    # Check whether another page exists
    has_next = len(rows) > limit

    # Only keep the requested number
    rows = rows[:limit]

    # -------------------------
    # Convert DB rows to API
    # response objects
    # -------------------------
    items = []

    for product, seller_product in rows:
        items.append(
            ProductListingResponse(
                product_id=product.id,
                name=product.name,
                description=product.description,
                category_id=product.category_id,
                seller_id=seller_product.seller_id,
                price=float(seller_product.price),
                stock=seller_product.stock,
                sku=seller_product.sku
            )
        )

    return ProductListResponse(
        items=items,
        limit=limit,
        offset=offset,
        has_next=has_next
    )    