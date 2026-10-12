from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_seller
from app.models.customer import Customer
from app.schemas.product import (
    ProductImageResponse,
    ProductListResponse,
    ProductListingResponse,
    SellerListingCreate,
)
from app.services.product import (
    create_product_listing,
    get_products,
)
from app.services.product_image import (
    delete_product_image,
    get_product_images,
    upload_product_image,
)


router = APIRouter(
    prefix="/products",
    tags=["Product"],
)


@router.post(
    "/",
)
def create_product(
    data: SellerListingCreate,
    seller: Customer = Depends(require_seller),
    db: Session = Depends(get_db),
):
    try:
        seller_product = create_product_listing(
            db=db,
            seller=seller,
            name=data.name,
            description=data.description,
            category_id=data.category_id,
            price=data.price,
            stock=data.stock,
            sku=data.sku,
        )

        if seller_product is None:
            raise HTTPException(
                status_code=404,
                detail="Category not found",
            )

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
            detail="Could not create product",
        )


@router.get(
    "/",
    response_model=ProductListResponse,
)
def get_products_route(
    category_id: int | None = None,
    search: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    sort: str | None = None,
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    db: Session = Depends(get_db),
):
    rows, has_next = get_products(
        db=db,
        category_id=category_id,
        search=search,
        min_price=min_price,
        max_price=max_price,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    items = [
    ProductListingResponse(
        product_id=product.id,
        name=product.name,
        description=product.description,
        category_id=product.category_id,
        seller_id=seller_product.seller_id,
        price=float(seller_product.price),
        stock=seller_product.stock,
        sku=seller_product.sku,
        images=[
            ProductImageResponse.model_validate(image)
            for image in sorted(
                product.images,
                key=lambda image: (
                    not image.is_primary,
                    image.sort_order,
                    image.id,
                ),
            )
        ],
    )
    for product, seller_product in rows
]
    return ProductListResponse(
        items=items,
        limit=limit,
        offset=offset,
        has_next=has_next,
    )
   
   


@router.post(
    "/{product_id}/images",
    response_model=ProductImageResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_product_image_route(
    product_id: int,
    image: UploadFile = File(...),
    is_primary: bool = False,
    sort_order: int = 0,
    seller: Customer = Depends(require_seller),
    db: Session = Depends(get_db),
):
    return upload_product_image(
        db=db,
        product_id=product_id,
        seller=seller,
        image=image,
        is_primary=is_primary,
        sort_order=sort_order,
    )


@router.get(
    "/{product_id}/images",
    response_model=list[ProductImageResponse],
)
def get_product_images_route(
    product_id: int,
    db: Session = Depends(get_db),
):
    return get_product_images(
        db=db,
        product_id=product_id,
    )


@router.delete(
    "/{product_id}/images/{image_id}",
)
def delete_product_image_route(
    product_id: int,
    image_id: int,
    seller: Customer = Depends(require_seller),
    db: Session = Depends(get_db),
):
    return delete_product_image(
        db=db,
        product_id=product_id,
        image_id=image_id,
        seller=seller,
    )