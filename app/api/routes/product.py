from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_async_db, require_seller
from app.models.customer import Customer
from app.models.review import Review
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
async def create_product(
    data: SellerListingCreate,
    seller: Customer = Depends(require_seller),
    db: AsyncSession = Depends(get_async_db),
):
    try:
        seller_product = await create_product_listing(
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
        await db.rollback()
        raise

    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not create product",
        )


@router.get(
    "/",
    response_model=ProductListResponse,
)
async def get_products_route(
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
    db: AsyncSession = Depends(get_async_db),
):
    rows, has_next = await get_products(
        db=db,
        category_id=category_id,
        search=search,
        min_price=min_price,
        max_price=max_price,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    product_ids = [product.id for product, _ in rows]
    rating_rows = []
    if product_ids:
        rating_rows = (await db.execute(
            select(Review.product_id, func.avg(Review.rating), func.count(Review.id))
            .where(Review.product_id.in_(product_ids), Review.is_hidden.is_(False))
            .group_by(Review.product_id)
        )).all()
    ratings = {product_id: (float(average), count) for product_id, average, count in rating_rows}
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
        average_rating=ratings.get(product.id, (None, 0))[0],
        review_count=ratings.get(product.id, (None, 0))[1],
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
async def upload_product_image_route(
    product_id: int,
    image: UploadFile = File(...),
    is_primary: bool = False,
    sort_order: int = 0,
    seller: Customer = Depends(require_seller),
    db: AsyncSession = Depends(get_async_db),
):
    return await upload_product_image(
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
async def get_product_images_route(
    product_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    return await get_product_images(
        db=db,
        product_id=product_id,
    )


@router.delete(
    "/{product_id}/images/{image_id}",
)
async def delete_product_image_route(
    product_id: int,
    image_id: int,
    seller: Customer = Depends(require_seller),
    db: AsyncSession = Depends(get_async_db),
):
    return await delete_product_image(
        db=db,
        product_id=product_id,
        image_id=image_id,
        seller=seller,
    )
