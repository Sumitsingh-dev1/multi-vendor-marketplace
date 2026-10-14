from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_async_db, require_seller
from app.models.customer import Customer
from app.models.seller_service_area import SellerServiceArea
from app.schemas.seller_service_area import (
    SellerServiceAreaCreate,
    SellerServiceAreaResponse
)


router = APIRouter(
    prefix="/seller/service-areas",
    tags=["Seller Service Areas"]
)


# =========================================================
# 1. ADD SERVICE AREA
# POST /seller/service-areas
# =========================================================

@router.post(
    "/",
    response_model=SellerServiceAreaResponse
)
async def create_service_area(
    data: SellerServiceAreaCreate,
    seller: Customer = Depends(require_seller),
    db: AsyncSession = Depends(get_async_db),
):
    # Check whether this seller already has this postal code
    result = await db.execute(
        select(SellerServiceArea).where(
            SellerServiceArea.seller_id == seller.id,
            SellerServiceArea.postal_code == data.postal_code
        )
    )
    existing = result.scalar_one_or_none()

    if existing is not None:
        raise HTTPException(
            status_code=400,
            detail="Postal code already added"
        )

    service_area = SellerServiceArea(
        seller_id=seller.id,
        postal_code=data.postal_code
    )

    db.add(service_area)
    await db.commit()
    await db.refresh(service_area)

    return service_area


# =========================================================
# 2. GET MY SERVICE AREAS
# GET /seller/service-areas
# =========================================================

@router.get(
    "/",
    response_model=list[SellerServiceAreaResponse]
)
async def get_my_service_areas(
    seller: Customer = Depends(require_seller),
    db: AsyncSession = Depends(get_async_db),
):
    statement = (
        select(SellerServiceArea)
        .where(
            SellerServiceArea.seller_id == seller.id
        )
    )

    result = await db.execute(statement)

    return result.scalars().all()


# =========================================================
# 3. DELETE SERVICE AREA
# DELETE /seller/service-areas/{service_area_id}
# =========================================================

@router.delete(
    "/{service_area_id}"
)
async def delete_service_area(
    service_area_id: int,
    seller: Customer = Depends(require_seller),
    db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(
        select(SellerServiceArea).where(
            SellerServiceArea.id == service_area_id,
            SellerServiceArea.seller_id == seller.id
        )
    )
    service_area = result.scalar_one_or_none()

    if service_area is None:
        raise HTTPException(
            status_code=404,
            detail="Service area not found"
        )

    await db.delete(service_area)
    await db.commit()

    return {
        "message": "Service area deleted successfully"
    }
