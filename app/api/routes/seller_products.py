from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_seller
from app.models.customer import Customer
from app.schemas.seller_product import (
    MySellerProductListResponse,
    MySellerProductResponse,
    SellerProductUpdate,
)
from app.services.seller_product import (
    get_seller_product,
    list_seller_products,
    update_seller_product,
)


router = APIRouter(
    prefix="/seller-products",
    tags=["Seller Products"],
)


@router.get(
    "/",
    response_model=MySellerProductListResponse,
)
def get_my_products(
    seller: Customer = Depends(require_seller),
    category_id: int | None = None,
    product_id: int | None = None,
    search: str | None = None,
    is_active: bool | None = None,
    sort: str = Query(default="newest"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    rows, has_next = list_seller_products(
        db=db,
        seller_id=seller.id,
        category_id=category_id,
        product_id=product_id,
        search=search,
        is_active=is_active,
        sort=sort,
        limit=limit,
        offset=offset,
    )

    items = [
        MySellerProductResponse(
            seller_product_id=seller_product.id,
            product_id=product.id,
            name=product.name,
            price=float(seller_product.price),
            stock=seller_product.stock,
            sku=seller_product.sku,
            is_active=seller_product.is_active,
        )
        for seller_product, product in rows
    ]

    return MySellerProductListResponse(
        items=items,
        limit=limit,
        offset=offset,
        has_next=has_next,
    )


@router.patch("/{seller_product_id}")
def update_my_seller_product(
    seller_product_id: int,
    data: SellerProductUpdate,
    seller: Customer = Depends(require_seller),
    db: Session = Depends(get_db),
):
    seller_product = update_seller_product(
        db=db,
        seller_id=seller.id,
        seller_product_id=seller_product_id,
        price=data.price,
        stock=data.stock,
        sku=data.sku,
        is_active=data.is_active,
    )

    if seller_product is None:
        raise HTTPException(
            status_code=404,
            detail="Seller product not found",
        )

    return {
        "message": "Seller product updated successfully",
    }


@router.get(
    "/{seller_product_id}",
    response_model=MySellerProductResponse,
)
def get_my_seller_product(
    seller_product_id: int,
    seller: Customer = Depends(require_seller),
    db: Session = Depends(get_db),
):
    result = get_seller_product(
        db=db,
        seller_id=seller.id,
        seller_product_id=seller_product_id,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Seller product not found",
        )

    seller_product, product = result

    return MySellerProductResponse(
        seller_product_id=seller_product.id,
        product_id=product.id,
        name=product.name,
        price=float(seller_product.price),
        stock=seller_product.stock,
        sku=seller_product.sku,
        is_active=seller_product.is_active,
    )