from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies import (
    get_db,
    get_current_customer,
    require_seller
)

from app.models.customer import (
    Customer,
    Cart,
    CartItem,
    SellerProduct,
    Product
)

from app.models.order import (
    Order,
    OrderStatus,
    OrderItem
)

from app.schemas.order import (
    OrderResponse,
    BuyNowRequest,
    OrderListItem,
    OrderDetailResponse,
    OrderItemResponse,
    SellerOrderItemResponse,
    OrderItemStatusUpdate
)


router = APIRouter(
    prefix="/order",
    tags=["Order"]
)


# =========================================================
# 1. CHECKOUT CART
# POST /order/
# =========================================================

@router.post(
    "/",
    response_model=OrderResponse
)
def create_order_from_cart(
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    # Find customer's cart
    cart = db.execute(
        select(Cart).where(
            Cart.customer_id == customer.id
        )
    ).scalar_one_or_none()

    if cart is None:
        raise HTTPException(
            status_code=404,
            detail="Cart not found"
        )

    # Get all items from the cart
    cart_items = db.execute(
        select(CartItem).where(
            CartItem.cart_id == cart.id
        )
    ).scalars().all()

    if not cart_items:
        raise HTTPException(
            status_code=400,
            detail="Cart is empty"
        )

    # Create order
    order = Order(
        customer_id=customer.id,
        status=OrderStatus.PENDING
    )

    db.add(order)

    # Get database-generated order.id
    db.flush()

    # Process every cart item
    for cart_item in cart_items:

        seller_product = db.execute(
            select(SellerProduct).where(
                SellerProduct.id == cart_item.seller_product_id
            )
        ).scalar_one_or_none()

        if seller_product is None:
            db.rollback()

            raise HTTPException(
                status_code=404,
                detail="Seller product not found"
            )

        # Check seller listing
        if not seller_product.is_active:
            db.rollback()

            raise HTTPException(
                status_code=400,
                detail="Seller product is inactive"
            )

        # Check current stock
        if cart_item.quantity > seller_product.stock:
            db.rollback()

            raise HTTPException(
                status_code=400,
                detail="Not enough stock"
            )

        # Create OrderItem
        order_item = OrderItem(
            order_id=order.id,
            seller_product_id=seller_product.id,
            quantity=cart_item.quantity,
            price=seller_product.price
        )

        db.add(order_item)

        # Reduce stock
        seller_product.stock -= cart_item.quantity

        # Remove item from cart
        db.delete(cart_item)

    # Save everything
    db.commit()

    return OrderResponse(
        order_id=order.id,
        status=order.status.value
    )


# =========================================================
# 2. BUY NOW
# POST /order/buy-now
# =========================================================

@router.post(
    "/buy-now",
    response_model=OrderResponse
)
def buy_now(
    data: BuyNowRequest,
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    # Find selected seller listing
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

    # Check listing is active
    if not seller_product.is_active:
        raise HTTPException(
            status_code=400,
            detail="Seller product is inactive"
        )

    # Check stock
    if data.quantity > seller_product.stock:
        raise HTTPException(
            status_code=400,
            detail="Not enough stock"
        )

    # Create order
    order = Order(
        customer_id=customer.id,
        status=OrderStatus.PENDING
    )

    db.add(order)

    # Get generated order.id
    db.flush()

    # Create order item
    order_item = OrderItem(
        order_id=order.id,
        seller_product_id=seller_product.id,
        quantity=data.quantity,
        price=seller_product.price
    )

    db.add(order_item)

    # Reduce stock
    seller_product.stock -= data.quantity

    # Save
    db.commit()

    return OrderResponse(
        order_id=order.id,
        status=order.status.value
    )


# =========================================================
# 3. CUSTOMER ORDER HISTORY
# GET /order/
# =========================================================

@router.get(
    "/",
    response_model=list[OrderListItem]
)
def get_my_orders(
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    statement = (
        select(Order)
        .where(
            Order.customer_id == customer.id
        )
        .order_by(
            Order.created_at.desc()
        )
    )

    result = db.execute(statement)

    orders = result.scalars().all()

    responses = []

    for order in orders:
        responses.append(
            OrderListItem(
                order_id=order.id,
                status=order.status.value
            )
        )

    return responses


# =========================================================
# 4. CUSTOMER ORDER DETAIL
# GET /order/{order_id}
# =========================================================

@router.get(
    "/{order_id}",
    response_model=OrderDetailResponse
)
def get_order(
    order_id: int,
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    # Find order belonging to current customer
    order = db.execute(
        select(Order).where(
            Order.id == order_id,
            Order.customer_id == customer.id
        )
    ).scalar_one_or_none()

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    # Get order items + seller product + product
    statement = (
        select(
            OrderItem,
            SellerProduct,
            Product
        )
        .join(
            SellerProduct,
            SellerProduct.id == OrderItem.seller_product_id
        )
        .join(
            Product,
            Product.id == SellerProduct.product_id
        )
        .where(
            OrderItem.order_id == order.id
        )
    )

    result = db.execute(statement)

    rows = result.all()

    items = []

    for order_item, seller_product, product in rows:
        items.append(
            OrderItemResponse(
                order_item_id=order_item.id,
                product_id=product.id,
                name=product.name,
                seller_product_id=seller_product.id,
                quantity=order_item.quantity,
                price=float(order_item.price),
                status=order_item.status
            )
        )

    return OrderDetailResponse(
        order_id=order.id,
        status=order.status.value,
        items=items
    )


# =========================================================
# 5. CANCEL ORDER
# PATCH /order/{order_id}/cancel
# =========================================================

@router.patch(
    "/{order_id}/cancel"
)
def cancel_order(
    order_id: int,
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    # Find customer's order
    order = db.execute(
        select(Order).where(
            Order.id == order_id,
            Order.customer_id == customer.id
        )
    ).scalar_one_or_none()

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    # Only pending orders can be cancelled
    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail="Only pending orders can be cancelled"
        )

    # Get order items
    order_items = db.execute(
        select(OrderItem).where(
            OrderItem.order_id == order.id
        )
    ).scalars().all()

    # Restore stock
    for order_item in order_items:

        seller_product = db.execute(
            select(SellerProduct).where(
                SellerProduct.id == order_item.seller_product_id
            )
        ).scalar_one_or_none()

        if seller_product is None:
            db.rollback()

            raise HTTPException(
                status_code=404,
                detail="Seller product not found"
            )

        seller_product.stock += order_item.quantity

    # Change order status
    order.status = OrderStatus.CANCELLED

    # Save
    db.commit()

    return {
        "message": "Order cancelled successfully"
    }


# =========================================================
# 6. SELLER ORDERS
# GET /order/seller
# =========================================================

@router.get(
    "/seller",
    response_model=list[SellerOrderItemResponse]
)
def get_seller_orders(
    seller: Customer = Depends(require_seller),
    db: Session = Depends(get_db)
):
    statement = (
        select(
            Order,
            OrderItem,
            SellerProduct,
            Product
        )
        .join(
            OrderItem,
            OrderItem.order_id == Order.id
        )
        .join(
            SellerProduct,
            SellerProduct.id == OrderItem.seller_product_id
        )
        .join(
            Product,
            Product.id == SellerProduct.product_id
        )
        .where(
            SellerProduct.seller_id == seller.id
        )
        .order_by(
            Order.created_at.desc()
        )
    )

    result = db.execute(statement)

    rows = result.all()

    responses = []

    for order, order_item, seller_product, product in rows:
        responses.append(
            SellerOrderItemResponse(
                order_id=order.id,
                order_item_id=order_item.id,
                product_id=product.id,
                name=product.name,
                quantity=order_item.quantity,
                price=float(order_item.price),
                status=order_item.status
            )
        )

    return responses


# =========================================================
# 7. SELLER UPDATE ORDER ITEM STATUS
# PATCH /order/items/{order_item_id}/status
# =========================================================

@router.patch(
    "/items/{order_item_id}/status"
)
def update_order_item_status(
    order_item_id: int,
    data: OrderItemStatusUpdate,
    seller: Customer = Depends(require_seller),
    db: Session = Depends(get_db)
):
    statement = (
        select(
            OrderItem,
            SellerProduct
        )
        .join(
            SellerProduct,
            SellerProduct.id == OrderItem.seller_product_id
        )
        .where(
            OrderItem.id == order_item_id,
            SellerProduct.seller_id == seller.id
        )
    )

    result = db.execute(statement)

    row = result.first()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Order item not found or does not belong to you"
        )

    order_item, seller_product = row

    order_item.status = data.status

    db.commit()

    db.refresh(order_item)

    return {
        "order_item_id": order_item.id,
        "status": order_item.status.value
    }