from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.address import Address
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.customer import Customer
from app.models.delivery_assignment import (
    DeliveryAssignment,
    DeliveryAssignmentStatus,
)
from app.models.order import Order, OrderItemStatus, OrderStatus
from app.models.order_item import OrderItem
from app.models.seller_product import SellerProduct
from app.models.seller_service_area import SellerServiceArea
from app.schemas.order import BuyNowRequest, CheckoutRequest


ORDER_ITEM_STATUS_TRANSITIONS = {
    OrderItemStatus.PENDING: {
        OrderItemStatus.CONFIRMED,
        OrderItemStatus.CANCELLED,
    },
    OrderItemStatus.CONFIRMED: {
        OrderItemStatus.SHIPPED,
        OrderItemStatus.CANCELLED,
    },
    OrderItemStatus.SHIPPED: set(),
    OrderItemStatus.DELIVERED: set(),
    OrderItemStatus.CANCELLED: set(),
}


def get_checkout_address(
    data: CheckoutRequest | BuyNowRequest,
    customer: Customer,
    db: Session,
):
    if data.address_id is not None:
        if any([
            data.latitude is not None,
            data.longitude is not None,
            data.address_line is not None,
            data.city is not None,
            data.state is not None,
            data.postal_code is not None,
        ]):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Provide either address_id or a new delivery "
                    "address, not both"
                ),
            )

        address = db.execute(
            select(Address).where(
                Address.id == data.address_id,
                Address.customer_id == customer.id,
            )
        ).scalar_one_or_none()

        if address is None:
            raise HTTPException(
                status_code=404,
                detail="Address not found",
            )

        return {
            "address_line": address.address_line,
            "city": address.city,
            "state": address.state,
            "postal_code": address.postal_code,
            "latitude": address.latitude,
            "longitude": address.longitude,
        }

    required_fields = [
        data.latitude,
        data.longitude,
        data.address_line,
        data.city,
        data.state,
        data.postal_code,
    ]

    if all(value is not None for value in required_fields):
        return {
            "address_line": data.address_line,
            "city": data.city,
            "state": data.state,
            "postal_code": data.postal_code,
            "latitude": data.latitude,
            "longitude": data.longitude,
        }

    raise HTTPException(
        status_code=400,
        detail=(
            "Provide either a saved address_id or a complete "
            "delivery address"
        ),
    )


def create_order_from_cart_service(
    db: Session,
    data: CheckoutRequest,
    customer: Customer,
):
    delivery_address = get_checkout_address(
        data,
        customer,
        db,
    )

    cart = db.execute(
        select(Cart).where(
            Cart.customer_id == customer.id,
        )
    ).scalar_one_or_none()

    if cart is None:
        raise HTTPException(
            status_code=404,
            detail="Cart not found",
        )

    cart_items = db.execute(
        select(CartItem).where(
            CartItem.cart_id == cart.id,
        )
    ).scalars().all()

    if not cart_items:
        raise HTTPException(
            status_code=400,
            detail="Cart is empty",
        )

    seller_products = []

    for cart_item in cart_items:
        seller_product = db.execute(
            select(SellerProduct).where(
                SellerProduct.id == cart_item.seller_product_id,
            )
        ).scalar_one_or_none()

        if seller_product is None:
            raise HTTPException(
                status_code=404,
                detail="Seller product not found",
            )

        if not seller_product.is_active:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Seller product {seller_product.id} "
                    "is inactive"
                ),
            )

        if cart_item.quantity > seller_product.stock:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Not enough stock for seller product "
                    f"{seller_product.id}"
                ),
            )

        service_area = db.execute(
            select(SellerServiceArea).where(
                SellerServiceArea.seller_id
                == seller_product.seller_id,
                SellerServiceArea.postal_code
                == delivery_address["postal_code"],
            )
        ).scalar_one_or_none()

        if service_area is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Seller does not deliver to postal code "
                    f"{delivery_address['postal_code']}"
                ),
            )

        seller_products.append(
            (cart_item, seller_product)
        )

    order = Order(
        customer_id=customer.id,
        status=OrderStatus.PENDING,
        delivery_address_line=delivery_address["address_line"],
        delivery_city=delivery_address["city"],
        delivery_state=delivery_address["state"],
        delivery_postal_code=delivery_address["postal_code"],
        delivery_latitude=delivery_address["latitude"],
        delivery_longitude=delivery_address["longitude"],
    )

    db.add(order)
    db.flush()

    for cart_item, seller_product in seller_products:
        order_item = OrderItem(
            order_id=order.id,
            seller_product_id=seller_product.id,
            quantity=cart_item.quantity,
            price=seller_product.price,
        )

        db.add(order_item)

        seller_product.stock -= cart_item.quantity

        db.delete(cart_item)

    db.commit()

    return order


def buy_now_service(
    db: Session,
    data: BuyNowRequest,
    customer: Customer,
):
    delivery_address = get_checkout_address(
        data,
        customer,
        db,
    )

    seller_product = db.execute(
        select(SellerProduct).where(
            SellerProduct.id == data.seller_product_id,
        )
    ).scalar_one_or_none()

    if seller_product is None:
        raise HTTPException(
            status_code=404,
            detail="Seller product not found",
        )

    if not seller_product.is_active:
        raise HTTPException(
            status_code=400,
            detail="Seller product is inactive",
        )

    if data.quantity > seller_product.stock:
        raise HTTPException(
            status_code=400,
            detail="Not enough stock",
        )

    service_area = db.execute(
        select(SellerServiceArea).where(
            SellerServiceArea.seller_id
            == seller_product.seller_id,
            SellerServiceArea.postal_code
            == delivery_address["postal_code"],
        )
    ).scalar_one_or_none()

    if service_area is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Seller does not deliver to postal code "
                f"{delivery_address['postal_code']}"
            ),
        )

    order = Order(
        customer_id=customer.id,
        status=OrderStatus.PENDING,
        delivery_address_line=delivery_address["address_line"],
        delivery_city=delivery_address["city"],
        delivery_state=delivery_address["state"],
        delivery_postal_code=delivery_address["postal_code"],
        delivery_latitude=delivery_address["latitude"],
        delivery_longitude=delivery_address["longitude"],
    )

    db.add(order)
    db.flush()

    order_item = OrderItem(
        order_id=order.id,
        seller_product_id=seller_product.id,
        quantity=data.quantity,
        price=seller_product.price,
    )

    db.add(order_item)

    seller_product.stock -= data.quantity

    db.commit()

    return order


def cancel_order_service(
    db: Session,
    order_id: int,
    customer_id: int,
):
    order = db.execute(
        select(Order).where(
            Order.id == order_id,
            Order.customer_id == customer_id,
        )
    ).scalar_one_or_none()

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found",
        )

    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail="Only pending orders can be cancelled",
        )

    active_assignment = db.execute(
        select(DeliveryAssignment).where(
            DeliveryAssignment.order_id == order_id,
            DeliveryAssignment.status.in_(
                {
                    DeliveryAssignmentStatus.ASSIGNED,
                    DeliveryAssignmentStatus.PICKED_UP,
                    DeliveryAssignmentStatus.OUT_FOR_DELIVERY,
                }
            ),
        )
    ).scalar_one_or_none()

    if active_assignment is not None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Order cannot be cancelled while "
                "delivery is in progress"
            ),
        )

    order_items = db.execute(
        select(OrderItem).where(
            OrderItem.order_id == order.id,
        )
    ).scalars().all()

    for order_item in order_items:
        seller_product = db.execute(
            select(SellerProduct).where(
                SellerProduct.id == order_item.seller_product_id,
            )
        ).scalar_one_or_none()

        if seller_product is None:
            db.rollback()

            raise HTTPException(
                status_code=404,
                detail="Seller product not found",
            )

        if order_item.status != OrderItemStatus.CANCELLED:
            seller_product.stock += order_item.quantity
            order_item.status = OrderItemStatus.CANCELLED

    order.status = OrderStatus.CANCELLED

    db.commit()

    return order


def update_order_item_status_service(
    db: Session,
    order_item_id: int,
    new_status: OrderItemStatus,
    seller_id: int,
):
    statement = (
        select(
            OrderItem,
            SellerProduct,
        )
        .join(
            SellerProduct,
            SellerProduct.id == OrderItem.seller_product_id,
        )
        .where(
            OrderItem.id == order_item_id,
            SellerProduct.seller_id == seller_id,
        )
    )

    result = db.execute(statement)
    row = result.first()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Order item not found or does not belong to you",
        )

    order_item, seller_product = row

    allowed_statuses = ORDER_ITEM_STATUS_TRANSITIONS[
        order_item.status
    ]

    if new_status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Cannot change order item status from "
                f"'{order_item.status.value}' "
                f"to '{new_status.value}'"
            ),
        )

    if new_status == OrderItemStatus.CANCELLED:
        seller_product.stock += order_item.quantity

    order_item.status = new_status

    order_items = db.execute(
        select(OrderItem).where(
            OrderItem.order_id == order_item.order_id
        )
    ).scalars().all()

    order = db.execute(
        select(Order).where(
            Order.id == order_item.order_id
        )
    ).scalar_one()

    active_items = [
        item
        for item in order_items
        if item.status != OrderItemStatus.CANCELLED
    ]

    if not active_items:
        order.status = OrderStatus.CANCELLED

    elif all(
        item.status == OrderItemStatus.SHIPPED
        for item in active_items
    ):
        order.status = OrderStatus.SHIPPED

    elif all(
        item.status in (
            OrderItemStatus.CONFIRMED,
            OrderItemStatus.SHIPPED,
        )
        for item in active_items
    ):
        order.status = OrderStatus.CONFIRMED

    else:
        order.status = OrderStatus.PENDING

    db.commit()
    db.refresh(order_item)

    return order_item