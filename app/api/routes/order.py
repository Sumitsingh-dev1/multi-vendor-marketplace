from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import (
    get_current_customer,
    get_async_db,
    require_seller,
)
from app.models.customer import Customer
from app.models.delivery_assignment import DeliveryAssignment
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.payment import Payment
from app.models.product import Product
from app.models.seller_product import SellerProduct
from app.schemas.order import (
    BuyNowRequest,
    CheckoutRequest,
    OrderDetailResponse,
    OrderItemResponse,
    OrderItemStatusUpdate,
    OrderListItem,
    OrderResponse,
    SellerOrderItemResponse,
)
from app.services.order import (
    buy_now_service,
    cancel_order_service,
    create_order_from_cart_service,
    update_order_item_status_service,
)


router = APIRouter(
    prefix="/order",
    tags=["Order"],
)


@router.post(
    "/",
    response_model=OrderResponse,
)
async def create_order_from_cart(
    data: CheckoutRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    customer: Customer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_async_db),
):
    order = await create_order_from_cart_service(
        db=db,
        data=data,
        customer=customer,
        idempotency_key=idempotency_key,
    )

    payment = (await db.execute(select(Payment).where(Payment.order_id == order.id))).scalars().first()
    return OrderResponse(
        order_id=order.id,
        status=order.status.value,
        payment_method=payment.payment_method if payment else None,
        payment_status=payment.status if payment else None,
        amount_due_paise=payment.amount_paise if payment else None,
    )


@router.post(
    "/buy-now",
    response_model=OrderResponse,
)
async def buy_now(
    data: BuyNowRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    customer: Customer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_async_db),
):
    order = await buy_now_service(
        db=db,
        data=data,
        customer=customer,
        idempotency_key=idempotency_key,
    )

    payment = (await db.execute(select(Payment).where(Payment.order_id == order.id))).scalars().first()
    return OrderResponse(
        order_id=order.id,
        status=order.status.value,
        payment_method=payment.payment_method if payment else None,
        payment_status=payment.status if payment else None,
        amount_due_paise=payment.amount_paise if payment else None,
    )


@router.get(
    "/",
    response_model=list[OrderListItem],
)
async def get_my_orders(
    customer: Customer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_async_db),
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

    result = await db.execute(statement)
    orders = result.scalars().all()

    responses = []

    for order in orders:
        responses.append(
            OrderListItem(
                order_id=order.id,
                status=order.status.value,
            )
        )

    return responses


@router.get(
    "/seller",
    response_model=list[SellerOrderItemResponse],
)
async def get_seller_orders(
    seller: Customer = Depends(require_seller),
    db: AsyncSession = Depends(get_async_db),
):
    statement = (
        select(
            Order,
            OrderItem,
            SellerProduct,
            Product,
        )
        .join(
            OrderItem,
            OrderItem.order_id == Order.id,
        )
        .join(
            SellerProduct,
            SellerProduct.id == OrderItem.seller_product_id,
        )
        .join(
            Product,
            Product.id == SellerProduct.product_id,
        )
        .where(
            SellerProduct.seller_id == seller.id,
        )
        .order_by(
            Order.created_at.desc(),
        )
    )

    result = await db.execute(statement)
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
                delivery_longitude=order.delivery_longitude,
            )
        )

    return responses


@router.get(
    "/{order_id}",
    response_model=OrderDetailResponse,
)
async def get_order(
    order_id: int,
    customer: Customer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(
        select(Order).where(
            Order.id == order_id,
            Order.customer_id == customer.id,
        )
    )
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found",
        )

    result = await db.execute(
        select(DeliveryAssignment)
        .where(
            DeliveryAssignment.order_id == order.id
        )
        .order_by(
            DeliveryAssignment.assigned_at.desc()
        )
    )
    latest_assignment = result.scalars().first()
    payment = (await db.execute(
        select(Payment).where(Payment.order_id == order.id)
    )).scalars().first()

    statement = (
        select(
            OrderItem,
            SellerProduct,
            Product,
        )
        .join(
            SellerProduct,
            SellerProduct.id == OrderItem.seller_product_id,
        )
        .join(
            Product,
            Product.id == SellerProduct.product_id,
        )
        .where(
            OrderItem.order_id == order.id,
        )
    )

    result = await db.execute(statement)
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
                status=order_item.status,
            )
        )

    return OrderDetailResponse(
        order_id=order.id,
        status=order.status.value,
        delivery_status=(
            latest_assignment.status
            if latest_assignment is not None
            else None
        ),
        payment_method=payment.payment_method if payment else None,
        payment_status=payment.status if payment else None,
        amount_due_paise=payment.amount_paise if payment else None,
        amount_collected_paise=payment.amount_collected_paise if payment else None,
        collected_at=payment.collected_at if payment else None,
        delivery_address_line=order.delivery_address_line,
        delivery_city=order.delivery_city,
        delivery_state=order.delivery_state,
        delivery_postal_code=order.delivery_postal_code,
        delivery_latitude=order.delivery_latitude,
        delivery_longitude=order.delivery_longitude,
        items=items,
    )


@router.patch(
    "/{order_id}/cancel",
)
async def cancel_order(
    order_id: int,
    customer: Customer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_async_db),
):
    await cancel_order_service(
        db=db,
        order_id=order_id,
        customer_id=customer.id,
    )

    return {
        "message": "Order cancelled successfully",
    }


@router.patch(
    "/items/{order_item_id}/status",
)
async def update_order_item_status(
    order_item_id: int,
    data: OrderItemStatusUpdate,
    seller: Customer = Depends(require_seller),
    db: AsyncSession = Depends(get_async_db),
):
    order_item = await update_order_item_status_service(
        db=db,
        order_item_id=order_item_id,
        new_status=data.status,
        seller_id=seller.id,
    )

    return {
        "order_item_id": order_item.id,
        "status": order_item.status.value,
    }
