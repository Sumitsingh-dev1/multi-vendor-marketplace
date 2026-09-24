from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_seller
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
def create_service_area(
    data: SellerServiceAreaCreate,
    seller: Customer = Depends(require_seller),
    db: Session = Depends(get_db)
):
    # Check whether this seller already has this postal code
    existing = db.execute(
        select(SellerServiceArea).where(
            SellerServiceArea.seller_id == seller.id,
            SellerServiceArea.postal_code == data.postal_code
        )
    ).scalar_one_or_none()

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
    db.commit()
    db.refresh(service_area)

    return service_area


# =========================================================
# 2. GET MY SERVICE AREAS
# GET /seller/service-areas
# =========================================================

@router.get(
    "/",
    response_model=list[SellerServiceAreaResponse]
)
def get_my_service_areas(
    seller: Customer = Depends(require_seller),
    db: Session = Depends(get_db)
):
    statement = (
        select(SellerServiceArea)
        .where(
            SellerServiceArea.seller_id == seller.id
        )
    )

    result = db.execute(statement)

    return result.scalars().all()


# =========================================================
# 3. DELETE SERVICE AREA
# DELETE /seller/service-areas/{service_area_id}
# =========================================================

@router.delete(
    "/{service_area_id}"
)
def delete_service_area(
    service_area_id: int,
    seller: Customer = Depends(require_seller),
    db: Session = Depends(get_db)
):
    service_area = db.execute(
        select(SellerServiceArea).where(
            SellerServiceArea.id == service_area_id,
            SellerServiceArea.seller_id == seller.id
        )
    ).scalar_one_or_none()

    if service_area is None:
        raise HTTPException(
            status_code=404,
            detail="Service area not found"
        )

    db.delete(service_area)
    db.commit()

    return {
        "message": "Service area deleted successfully"
    }