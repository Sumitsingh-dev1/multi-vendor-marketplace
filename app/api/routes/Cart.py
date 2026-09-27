from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_current_customer, get_db
from app.models.customer import Customer
from app.schemas.cart import (
    CartItemCreate,
    CartItemResponse,
    CartItemUpdate,
    CartResponse,
)
from app.services.cart import (
    add_item_to_cart,
    delete_cart_item,
    get_customer_cart,
    update_cart_item,
)


router = APIRouter(
    prefix="/cart",
    tags=["Cart"],
)


@router.post("/items")
def add_to_cart(
    data: CartItemCreate,
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    try:
        add_item_to_cart(
            db=db,
            customer_id=customer.id,
            seller_product_id=data.seller_product_id,
            quantity=data.quantity,
        )
    except HTTPException:
        raise

    return {
        "message": "Product added to cart successfully"
    }


@router.get("/", response_model=CartResponse)
def get_cart(
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    cart_id, cart_items = get_customer_cart(
        db=db,
        customer_id=customer.id,
    )

    if cart_id is None:
        return CartResponse(
            cart_id=0,
            items=[],
        )

    items = [
        CartItemResponse(
            cart_item_id=cart_item.id,
            seller_product_id=seller_product.id,
            product_id=product.id,
            name=product.name,
            price=float(seller_product.price),
            quantity=cart_item.quantity,
        )
        for cart_item, seller_product, product in cart_items
    ]

    return CartResponse(
        cart_id=cart_id,
        items=items,
    )


@router.patch("/items/{cart_item_id}")
def update_cart_item_route(
    cart_item_id: int,
    data: CartItemUpdate,
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    update_cart_item(
        db=db,
        customer_id=customer.id,
        cart_item_id=cart_item_id,
        quantity=data.quantity,
    )

    return {
        "message": "Cart quantity updated successfully"
    }


@router.delete("/items/{cart_item_id}")
def delete_cart_item_route(
    cart_item_id: int,
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    delete_cart_item(
        db=db,
        customer_id=customer.id,
        cart_item_id=cart_item_id,
    )

    return {
        "message": "Cart item removed successfully"
    }