from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_customer
from app.models.customer import (
    Customer,
    Cart,
    CartItem,
    SellerProduct,
    Product
)
from app.schemas.cart import CartItemCreate,CartResponse,CartItemResponse,CartItemUpdate


router = APIRouter(
    prefix="/cart",
    tags=["Cart"]
)



# ==========================================
# ADD ITEM TO CART
# ==========================================

@router.post("/items")
def add_to_cart(
    data: CartItemCreate,
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    # 1. Find SellerProduct
    seller_product = db.execute(
        select(SellerProduct).where(
            SellerProduct.id == data.seller_product_id
        )
    ).scalar_one_or_none()

    if seller_product is None:
        raise HTTPException(
            status_code=404,
            detail="Seller product not found"
        )

    # 2. Check active
    if not seller_product.is_active:
        raise HTTPException(
            status_code=400,
            detail="Seller product is inactive"
        )

    # 3. Check stock
    if data.quantity > seller_product.stock:
        raise HTTPException(
            status_code=400,
            detail="Not enough stock"
        )

    # 4. Find customer's cart
    cart = db.execute(
        select(Cart).where(
            Cart.customer_id == customer.id
        )
    ).scalar_one_or_none()

    if cart is None:
         cart = Cart(
        customer_id=customer.id
    )

    db.add(cart)
    db.flush()
        

    # 5. Check whether item already exists
    cart_item = db.execute(
        select(CartItem).where(
            CartItem.cart_id == cart.id,
            CartItem.seller_product_id == data.seller_product_id
        )
    ).scalar_one_or_none()

    # 6. Update existing item
    if cart_item is not None:

        new_quantity = (
            cart_item.quantity + data.quantity
        )

        if new_quantity > seller_product.stock:
            raise HTTPException(
                status_code=400,
                detail="Not enough stock"
            )

        cart_item.quantity = new_quantity

    # 7. Create new item
    else:

        cart_item = CartItem(
            cart_id=cart.id,
            seller_product_id=data.seller_product_id,
            quantity=data.quantity
        )

        db.add(cart_item)

    # 8. Save
    db.commit()

    return {
        "message": "Product added to cart successfully"
    }
@router.get("/", response_model=CartResponse)
def get_cart(
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    cart = db.execute(
        select(Cart).where(
            Cart.customer_id == customer.id
        )
    ).scalar_one_or_none()

    if cart is None:
        return CartResponse(
            cart_id=0,
            items=[]
        )

    statement = (
        select(CartItem, SellerProduct, Product)
        .join(
            SellerProduct,
            SellerProduct.id == CartItem.seller_product_id
        )
        .join(
            Product,
            Product.id == SellerProduct.product_id
        )
        .where(
            CartItem.cart_id == cart.id
        )
    )

    result = db.execute(statement)
    rows = result.all()

    items = []

    for cart_item, seller_product, product in rows:
        items.append(
            CartItemResponse(
                cart_item_id=cart_item.id,
                seller_product_id=seller_product.id,
                product_id=product.id,
                name=product.name,
                price=float(seller_product.price),
                quantity=cart_item.quantity
            )
        )

    return CartResponse(
        cart_id=cart.id,
        items=items
    )
@router.patch("/items/{cart_item_id}")
def update_cart_item(
    cart_item_id: int,
    data: CartItemUpdate,
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    cart_item = db.execute(
        select(CartItem)
        .join(Cart)
        .where(
            CartItem.id == cart_item_id,
            Cart.customer_id == customer.id
        )
    ).scalar_one_or_none()

    if cart_item is None:
        raise HTTPException(
            status_code=404,
            detail="Cart item not found"
        )

    seller_product = db.execute(
        select(SellerProduct).where(
            SellerProduct.id == cart_item.seller_product_id
        )
    ).scalar_one_or_none()

    if seller_product is None:
        raise HTTPException(
            status_code=404,
            detail="Seller product not found"
        )

    if not seller_product.is_active:
        raise HTTPException(
            status_code=400,
            detail="Seller product is inactive"
        )

    if data.quantity > seller_product.stock:
        raise HTTPException(
            status_code=400,
            detail="Not enough stock"
        )

    cart_item.quantity = data.quantity

    db.commit()

    return {
        "message": "Cart quantity updated successfully"
    }
@router.delete("/items/{cart_item_id}")
def delete_cart_item(
    cart_item_id: int,
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    cart_item = db.execute(
        select(CartItem)
        .join(Cart)
        .where(
            CartItem.id == cart_item_id,
            Cart.customer_id == customer.id
        )
    ).scalar_one_or_none()

    if cart_item is None:
        raise HTTPException(
            status_code=404,
            detail="Cart item not found"
        )

    db.delete(cart_item)
    db.commit()

    return {
        "message": "Cart item removed successfully"
    }
   

