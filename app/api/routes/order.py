from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies import (
    get_db,
    get_current_customer,
    require_seller,
    require_admin
)

from app.models.customer import (
    Customer,
    Cart,
    CartItem,
    SellerProduct,
    Product
)

from app.models.address import Address

from app.models.order import (
    Order,
    OrderStatus,
    OrderItem,
    OrderItemStatus
)

from app.models.seller_service_area import SellerServiceArea

from app.schemas.order import (
    OrderResponse,
    BuyNowRequest,
    CheckoutRequest,
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
# HELPER: GET FINAL CHECKOUT ADDRESS
# =========================================================

def get_checkout_address(
    data,
    customer: Customer,
    db: Session
):
    # -----------------------------------------------------
    # Option 1: Use a saved address
    # -----------------------------------------------------

    if data.address_id is not None:

        # Do not allow both saved address and manual/map
        # address data at the same time.
        if any([
            data.latitude is not None,
            data.longitude is not None,
            data.address_line is not None,
            data.city is not None,
            data.state is not None,
            data.postal_code is not None
        ]):
            raise HTTPException(
                status_code=400,
                detail="Provide either address_id or a new delivery address, not both"
            )

        address = db.execute(
            select(Address).where(
                Address.id == data.address_id,
                Address.customer_id == customer.id
            )
        ).scalar_one_or_none()

        if address is None:
            raise HTTPException(
                status_code=404,
                detail="Address not found"
            )

        return {
            "address_line": address.address_line,
            "city": address.city,
            "state": address.state,
            "postal_code": address.postal_code,
            "latitude": address.latitude,
            "longitude": address.longitude
        }

    # -----------------------------------------------------
    # Option 2: Use current location / map pin / manual
    # address
    # -----------------------------------------------------

    required_fields = [
        data.latitude,
        data.longitude,
        data.address_line,
        data.city,
        data.state,
        data.postal_code
    ]

    if all(value is not None for value in required_fields):

        return {
            "address_line": data.address_line,
            "city": data.city,
            "state": data.state,
            "postal_code": data.postal_code,
            "latitude": data.latitude,
            "longitude": data.longitude
        }

    # -----------------------------------------------------
    # No valid address
    # -----------------------------------------------------

    raise HTTPException(
        status_code=400,
        detail=(
            "Provide either a saved address_id or a complete "
            "delivery address"
        )
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
    data: CheckoutRequest,
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    # -----------------------------------------------------
    # Get final delivery address
    # -----------------------------------------------------

    delivery_address = get_checkout_address(
        data,
        customer,
        db
    )

    # -----------------------------------------------------
    # Find customer's cart
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Get cart items
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # VALIDATION PHASE
    # No order or stock changes happen here
    # -----------------------------------------------------

    seller_products = []

    for cart_item in cart_items:

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

        # Check listing is active
        if not seller_product.is_active:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Seller product {seller_product.id} "
                    "is inactive"
                )
            )

        # Check stock
        if cart_item.quantity > seller_product.stock:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Not enough stock for seller product "
                    f"{seller_product.id}"
                )
            )

        # Check seller serviceability
        service_area = db.execute(
            select(SellerServiceArea).where(
                SellerServiceArea.seller_id == seller_product.seller_id,
                SellerServiceArea.postal_code == delivery_address["postal_code"]
            )
        ).scalar_one_or_none()

        if service_area is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Seller does not deliver to postal code "
                    f"{delivery_address['postal_code']}"
                )
            )

        seller_products.append(
            (cart_item, seller_product)
        )

    # -----------------------------------------------------
    # All validation passed
    # Create order
    # -----------------------------------------------------

    order = Order(
        customer_id=customer.id,
        status=OrderStatus.PENDING,
        delivery_address_line=delivery_address["address_line"],
        delivery_city=delivery_address["city"],
        delivery_state=delivery_address["state"],
        delivery_postal_code=delivery_address["postal_code"],
        delivery_latitude=delivery_address["latitude"],
        delivery_longitude=delivery_address["longitude"]
    )

    db.add(order)

    # Get database-generated order ID
    db.flush()

    # -----------------------------------------------------
    # Create order items
    # -----------------------------------------------------

    for cart_item, seller_product in seller_products:

        order_item = OrderItem(
            order_id=order.id,
            seller_product_id=seller_product.id,
            quantity=cart_item.quantity,
            price=seller_product.price
        )

        db.add(order_item)

        # Reduce stock
        seller_product.stock -= cart_item.quantity

        # Remove from cart
        db.delete(cart_item)

    # -----------------------------------------------------
    # Save
    # -----------------------------------------------------

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
    # -----------------------------------------------------
    # Get final delivery address
    # -----------------------------------------------------

    delivery_address = get_checkout_address(
        data,
        customer,
        db
    )

    # -----------------------------------------------------
    # Find seller product
    # -----------------------------------------------------

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

    # Check listing
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

    # -----------------------------------------------------
    # Check seller serviceability
    # -----------------------------------------------------

    service_area = db.execute(
        select(SellerServiceArea).where(
            SellerServiceArea.seller_id == seller_product.seller_id,
            SellerServiceArea.postal_code == delivery_address["postal_code"]
        )
    ).scalar_one_or_none()

    if service_area is None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Seller does not deliver to postal code "
                f"{delivery_address['postal_code']}"
            )
        )

    # -----------------------------------------------------
    # Create order
    # -----------------------------------------------------

    order = Order(
        customer_id=customer.id,
        status=OrderStatus.PENDING,
        delivery_address_line=delivery_address["address_line"],
        delivery_city=delivery_address["city"],
        delivery_state=delivery_address["state"],
        delivery_postal_code=delivery_address["postal_code"],
        delivery_latitude=delivery_address["latitude"],
        delivery_longitude=delivery_address["longitude"]
    )

    db.add(order)

    # Get generated order ID
    db.flush()

    # -----------------------------------------------------
    # Create order item
    # -----------------------------------------------------

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
# 4. SELLER ORDERS
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
                status=order_item.status,
                delivery_address_line=order.delivery_address_line,
                delivery_city=order.delivery_city,
                delivery_state=order.delivery_state,
                delivery_postal_code=order.delivery_postal_code,
                delivery_latitude=order.delivery_latitude,
                delivery_longitude=order.delivery_longitude
            )
        )

    return responses


# =========================================================
# 5. CUSTOMER ORDER DETAIL
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

    # -----------------------------------------------------
    # Get order items + seller product + product
    # -----------------------------------------------------

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
        delivery_address_line=order.delivery_address_line,
        delivery_city=order.delivery_city,
        delivery_state=order.delivery_state,
        delivery_postal_code=order.delivery_postal_code,
        delivery_latitude=order.delivery_latitude,
        delivery_longitude=order.delivery_longitude,
        items=items
    )


# =========================================================
# 6. CANCEL ORDER
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

    db.commit()

    return {
        "message": "Order cancelled successfully"
    }


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

    # Update item status
    order_item.status = data.status

    # Get all items belonging to this order
    order_items = db.execute(
        select(OrderItem).where(
            OrderItem.order_id == order_item.order_id
        )
    ).scalars().all()

    # Find the parent order
    order = db.execute(
        select(Order).where(
            Order.id == order_item.order_id
        )
    ).scalar_one()

    # Ignore cancelled items when checking active progress
    active_items = [
        item
        for item in order_items
        if item.status != OrderItemStatus.CANCELLED
    ]

    # All items cancelled
    if not active_items:
        order.status = OrderStatus.CANCELLED

    # All active items delivered
    elif all(
        item.status == OrderItemStatus.DELIVERED
        for item in active_items
    ):
        order.status = OrderStatus.DELIVERED

    # All active items are shipped or delivered
    elif all(
        item.status in (
            OrderItemStatus.SHIPPED,
            OrderItemStatus.DELIVERED
        )
        for item in active_items
    ):
        order.status = OrderStatus.SHIPPED

    # All active items are confirmed or further along
    elif all(
        item.status in (
            OrderItemStatus.CONFIRMED,
            OrderItemStatus.SHIPPED,
            OrderItemStatus.DELIVERED
        )
        for item in active_items
    ):
        order.status = OrderStatus.CONFIRMED

    # Otherwise
    else:
        order.status = OrderStatus.PENDING

    db.commit()

    db.refresh(order_item)

    return {
        "order_item_id": order_item.id,
        "status": order_item.status.value
    }
# =========================================================
# 8. ADMIN UPDATE ORDER ITEM STATUS
# PATCH /order/admin/items/{order_item_id}/status
# =========================================================

@router.patch(
    "/admin/items/{order_item_id}/status"
)
def admin_update_order_item_status(
    order_item_id: int,
    data: OrderItemStatusUpdate,
    admin: Customer = Depends(require_admin),
    db: Session = Depends(get_db)
):
    # Find the order item
    order_item = db.execute(
        select(OrderItem).where(
            OrderItem.id == order_item_id
        )
    ).scalar_one_or_none()

    if order_item is None:
        raise HTTPException(
            status_code=404,
            detail="Order item not found"
        )

    # Update item status
    order_item.status = data.status

    # Get all items belonging to this order
    order_items = db.execute(
        select(OrderItem).where(
            OrderItem.order_id == order_item.order_id
        )
    ).scalars().all()

    # Find parent order
    order = db.execute(
        select(Order).where(
            Order.id == order_item.order_id
        )
    ).scalar_one()

    # Ignore cancelled items when checking progress
    active_items = [
        item
        for item in order_items
        if item.status != OrderItemStatus.CANCELLED
    ]

    # All items cancelled
    if not active_items:
        order.status = OrderStatus.CANCELLED

    # All active items delivered
    elif all(
        item.status == OrderItemStatus.DELIVERED
        for item in active_items
    ):
        order.status = OrderStatus.DELIVERED

    # All active items shipped or delivered
    elif all(
        item.status in (
            OrderItemStatus.SHIPPED,
            OrderItemStatus.DELIVERED
        )
        for item in active_items
    ):
        order.status = OrderStatus.SHIPPED

    # All active items confirmed or further along
    elif all(
        item.status in (
            OrderItemStatus.CONFIRMED,
            OrderItemStatus.SHIPPED,
            OrderItemStatus.DELIVERED
        )
        for item in active_items
    ):
        order.status = OrderStatus.CONFIRMED

    # Otherwise
    else:
        order.status = OrderStatus.PENDING

    db.commit()

    db.refresh(order_item)

    return {
        "order_item_id": order_item.id,
        "status": order_item.status.value
    }