from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_customer
from app.models.customer import Customer
from app.models.address import Address
from app.schemas.address import (
    AddressCreate,
    AddressResponse,
    AddressUpdate
)


router = APIRouter(
    prefix="/address",
    tags=["Address"]
)


# =========================================================
# 1. CREATE ADDRESS
# POST /address/
# =========================================================

@router.post(
    "/",
    response_model=AddressResponse
)
def create_address(
    data: AddressCreate,
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    address = Address(
        customer_id=customer.id,
        label=data.label,
        latitude=data.latitude,
        longitude=data.longitude,
        address_line=data.address_line,
        city=data.city,
        state=data.state,
        postal_code=data.postal_code
    )

    db.add(address)
    db.commit()
    db.refresh(address)

    return address


# =========================================================
# 2. GET ALL MY ADDRESSES
# GET /address/
# =========================================================

@router.get(
    "/",
    response_model=list[AddressResponse]
)
def get_my_addresses(
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    statement = (
        select(Address)
        .where(
            Address.customer_id == customer.id
        )
    )

    result = db.execute(statement)

    addresses = result.scalars().all()

    return addresses


# =========================================================
# 3. GET ONE ADDRESS
# GET /address/{address_id}
# =========================================================

@router.get(
    "/{address_id}",
    response_model=AddressResponse
)
def get_address(
    address_id: int,
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    address = db.execute(
        select(Address).where(
            Address.id == address_id,
            Address.customer_id == customer.id
        )
    ).scalar_one_or_none()

    if address is None:
        raise HTTPException(
            status_code=404,
            detail="Address not found"
        )

    return address


# =========================================================
# 4. UPDATE ADDRESS
# PATCH /address/{address_id}
# =========================================================

@router.patch(
    "/{address_id}",
    response_model=AddressResponse
)
def update_address(
    address_id: int,
    data: AddressUpdate,
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    address = db.execute(
        select(Address).where(
            Address.id == address_id,
            Address.customer_id == customer.id
        )
    ).scalar_one_or_none()

    if address is None:
        raise HTTPException(
            status_code=404,
            detail="Address not found"
        )

    if data.label is not None:
        address.label = data.label

    if data.latitude is not None:
        address.latitude = data.latitude

    if data.longitude is not None:
        address.longitude = data.longitude

    if data.address_line is not None:
        address.address_line = data.address_line

    if data.city is not None:
        address.city = data.city

    if data.state is not None:
        address.state = data.state

    if data.postal_code is not None:
        address.postal_code = data.postal_code

    db.commit()
    db.refresh(address)

    return address


# =========================================================
# 5. DELETE ADDRESS
# DELETE /address/{address_id}
# =========================================================

@router.delete(
    "/{address_id}"
)
def delete_address(
    address_id: int,
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    address = db.execute(
        select(Address).where(
            Address.id == address_id,
            Address.customer_id == customer.id
        )
    ).scalar_one_or_none()

    if address is None:
        raise HTTPException(
            status_code=404,
            detail="Address not found"
        )

    db.delete(address)
    db.commit()

    return {
        "message": "Address deleted successfully"
    }