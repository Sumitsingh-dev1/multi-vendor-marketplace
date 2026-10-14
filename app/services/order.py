from fastapi import HTTPException
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.address import Address
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.customer import Customer
from app.models.delivery_assignment import DeliveryAssignment, DeliveryAssignmentStatus
from app.models.order import Order, OrderItemStatus, OrderStatus
from app.models.order_item import OrderItem
from app.models.seller_product import SellerProduct
from app.models.seller_service_area import SellerServiceArea
from app.models.payment import Payment, PaymentMethod, PaymentStatus
from app.schemas.order import BuyNowRequest, CheckoutRequest
from app.services.notification import notify

ORDER_ITEM_STATUS_TRANSITIONS = {
    OrderItemStatus.PENDING: {OrderItemStatus.CONFIRMED, OrderItemStatus.CANCELLED},
    OrderItemStatus.CONFIRMED: {OrderItemStatus.SHIPPED, OrderItemStatus.CANCELLED},
    OrderItemStatus.SHIPPED: set(), OrderItemStatus.DELIVERED: set(), OrderItemStatus.CANCELLED: set(),
}

async def get_checkout_address(data: CheckoutRequest | BuyNowRequest, customer: Customer, db: AsyncSession):
    if data.address_id is not None:
        if any(v is not None for v in (data.latitude, data.longitude, data.address_line, data.city, data.state, data.postal_code)):
            raise HTTPException(400, "Provide either address_id or a new delivery address, not both")
        address = (await db.execute(select(Address).where(Address.id == data.address_id, Address.customer_id == customer.id))).scalar_one_or_none()
        if address is None: raise HTTPException(404, "Address not found")
        return {"address_line": address.address_line, "city": address.city, "state": address.state, "postal_code": address.postal_code, "latitude": address.latitude, "longitude": address.longitude}
    values = (data.latitude, data.longitude, data.address_line, data.city, data.state, data.postal_code)
    if all(v is not None for v in values): return dict(zip(("latitude", "longitude", "address_line", "city", "state", "postal_code"), values))
    raise HTTPException(400, "Provide either a saved address_id or a complete delivery address")

async def _existing_key(db, customer_id, key, operation):
    if not key: return None
    return (await db.execute(select(Order).where(Order.customer_id == customer_id, Order.idempotency_key == key, Order.idempotency_operation == operation))).scalar_one_or_none()

async def _lock_products(db, quantities):
    rows = (await db.execute(select(SellerProduct).where(SellerProduct.id.in_(sorted(quantities))).order_by(SellerProduct.id).with_for_update())).scalars().all()
    products = {p.id: p for p in rows}
    for product_id, quantity in quantities.items():
        product = products.get(product_id)
        if product is None: raise HTTPException(404, f"Seller product {product_id} not found")
        if not product.is_active: raise HTTPException(400, f"Seller product {product_id} is inactive")
        if quantity > product.stock: raise HTTPException(409, f"Not enough stock for seller product {product_id}")
    return products

async def _create_order(db, customer, address, lines, key, operation, payment_method):
    quantities = {}
    for product_id, quantity in lines: quantities[product_id] = quantities.get(product_id, 0) + quantity
    products = await _lock_products(db, quantities)
    sellers = {p.seller_id for p in products.values()}
    covered = set((await db.execute(select(SellerServiceArea.seller_id).where(SellerServiceArea.seller_id.in_(sellers), SellerServiceArea.postal_code == address["postal_code"]))).scalars())
    if sellers - covered: raise HTTPException(400, f"A seller does not deliver to postal code {address['postal_code']}")
    order = Order(customer_id=customer.id, idempotency_key=key, idempotency_operation=operation, status=OrderStatus.PENDING, delivery_address_line=address["address_line"], delivery_city=address["city"], delivery_state=address["state"], delivery_postal_code=address["postal_code"], delivery_latitude=address["latitude"], delivery_longitude=address["longitude"])
    db.add(order); await db.flush()
    for product_id, quantity in quantities.items():
        product = products[product_id]
        db.add(OrderItem(order_id=order.id, seller_product_id=product.id, quantity=quantity, price=product.price))
        product.stock -= quantity
    if payment_method != PaymentMethod.COD:
        raise HTTPException(503, "Online payment checkout is unavailable until Razorpay is configured and verified")
    order_items = (await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))).scalars().all()
    amount_paise = int((sum((Decimal(str(item.price)) * item.quantity for item in order_items), start=Decimal("0")) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if amount_paise <= 0: raise HTTPException(400, "Order amount must be greater than zero")
    db.add(Payment(order_id=order.id, amount_paise=amount_paise, currency="INR", payment_method=PaymentMethod.COD, status=PaymentStatus.PENDING_COLLECTION))
    await notify(db, customer.id, "order_placed", "Order placed", "Your order has been placed.", "order", order.id, f"order:{order.id}:placed:customer")
    for seller_id in sellers:
        await notify(db, seller_id, "new_order_item", "New order item", "You have a new order item to process.", "order", order.id, f"order:{order.id}:placed:seller:{seller_id}")
    return order

async def _create_with_lines(db, data, customer, lines, key, operation, payment_method):
    key = key.strip() if key else None
    if not key: key = None
    existing = await _existing_key(db, customer.id, key, operation)
    if existing: return existing
    address = await get_checkout_address(data, customer, db)
    try:
        order = await _create_order(db, customer, address, lines, key, operation, payment_method)
        await db.commit()
        return order
    except IntegrityError:
        await db.rollback()
        existing = await _existing_key(db, customer.id, key, operation)
        if existing: return existing
        raise
    except Exception:
        await db.rollback(); raise

async def create_order_from_cart_service(db: AsyncSession, data: CheckoutRequest, customer: Customer, idempotency_key: str | None = None):
    key = idempotency_key.strip() if idempotency_key else None
    if not key: key = None
    existing = await _existing_key(db, customer.id, key, "checkout")
    if existing: return existing
    address = await get_checkout_address(data, customer, db)
    cart = (await db.execute(select(Cart).where(Cart.customer_id == customer.id).with_for_update())).scalar_one_or_none()
    if cart is None: raise HTTPException(404, "Cart not found")
    existing = await _existing_key(db, customer.id, key, "checkout")
    if existing: return existing
    items = (await db.execute(select(CartItem).where(CartItem.cart_id == cart.id).order_by(CartItem.seller_product_id).with_for_update())).scalars().all()
    if not items: raise HTTPException(400, "Cart is empty")
    try:
        order = await _create_order(db, customer, address, [(i.seller_product_id, i.quantity) for i in items], key, "checkout", data.payment_method)
        for item in items: await db.delete(item)
        await db.commit()
        return order
    except IntegrityError:
        await db.rollback()
        existing = await _existing_key(db, customer.id, key, "checkout")
        if existing: return existing
        raise
    except Exception:
        await db.rollback(); raise

async def buy_now_service(db: AsyncSession, data: BuyNowRequest, customer: Customer, idempotency_key: str | None = None):
    return await _create_with_lines(db, data, customer, [(data.seller_product_id, data.quantity)], idempotency_key, "buy_now", data.payment_method)

async def _sync_order(order, items):
    active = [i for i in items if i.status != OrderItemStatus.CANCELLED]
    if not active: order.status = OrderStatus.CANCELLED
    elif all(i.status == OrderItemStatus.DELIVERED for i in active): order.status = OrderStatus.DELIVERED
    elif all(i.status == OrderItemStatus.SHIPPED for i in active): order.status = OrderStatus.SHIPPED
    elif all(i.status in {OrderItemStatus.CONFIRMED, OrderItemStatus.SHIPPED} for i in active): order.status = OrderStatus.CONFIRMED
    else: order.status = OrderStatus.PENDING

async def cancel_order_service(db: AsyncSession, order_id: int, customer_id: int):
    try:
        order = (await db.execute(select(Order).where(Order.id == order_id, Order.customer_id == customer_id).with_for_update())).scalar_one_or_none()
        if order is None: raise HTTPException(404, "Order not found")
        if order.status != OrderStatus.PENDING: raise HTTPException(400, "Only pending orders can be cancelled")
        assignment = (await db.execute(select(DeliveryAssignment).where(DeliveryAssignment.order_id == order_id).with_for_update())).scalars().first()
        if assignment and assignment.status != DeliveryAssignmentStatus.CANCELLED: raise HTTPException(400, "Order cannot be cancelled once delivery is assigned")
        items = (await db.execute(select(OrderItem).where(OrderItem.order_id == order_id).with_for_update())).scalars().all()
        products = await _lock_products(db, {i.seller_product_id: 0 for i in items})
        for item in items:
            if item.status != OrderItemStatus.CANCELLED: products[item.seller_product_id].stock += item.quantity; item.status = OrderItemStatus.CANCELLED
        payment = (await db.execute(select(Payment).where(Payment.order_id == order.id).with_for_update())).scalar_one_or_none()
        if payment and payment.payment_method == PaymentMethod.COD and payment.status == PaymentStatus.PENDING_COLLECTION:
            payment.status = PaymentStatus.FAILED
            payment.failure_reason = "Order cancelled before COD collection"
        await notify(db, customer_id, "order_cancelled", "Order cancelled", "Your order has been cancelled.", "order", order.id, f"order:{order.id}:cancelled:customer")
        for seller_id in {product.seller_id for product in products.values()}:
            await notify(db, seller_id, "order_item_cancelled", "Order item cancelled", "An item in an order has been cancelled.", "order", order.id, f"order:{order.id}:cancelled:seller:{seller_id}")
        await _sync_order(order, items); await db.commit(); return order
    except Exception:
        await db.rollback(); raise

async def update_order_item_status_service(db: AsyncSession, order_item_id: int, new_status: OrderItemStatus, seller_id: int):
    try:
        row = (await db.execute(select(OrderItem, SellerProduct, Order).join(SellerProduct, SellerProduct.id == OrderItem.seller_product_id).join(Order, Order.id == OrderItem.order_id).where(OrderItem.id == order_item_id, SellerProduct.seller_id == seller_id).with_for_update())).first()
        if row is None: raise HTTPException(404, "Order item not found or does not belong to you")
        item, product, order = row
        if new_status not in ORDER_ITEM_STATUS_TRANSITIONS[item.status]: raise HTTPException(400, f"Cannot change order item status from '{item.status.value}' to '{new_status.value}'")
        assignment = (await db.execute(select(DeliveryAssignment).where(DeliveryAssignment.order_id == order.id).with_for_update())).scalars().first()
        if assignment and assignment.status != DeliveryAssignmentStatus.CANCELLED: raise HTTPException(400, "Order item cannot change after delivery is assigned")
        if new_status == OrderItemStatus.CANCELLED: product.stock += item.quantity
        item.status = new_status
        if new_status in {OrderItemStatus.CONFIRMED, OrderItemStatus.SHIPPED}:
            await notify(db, order.customer_id, f"order_item_{new_status.value}", f"Order item {new_status.value}", f"An item in your order has been {new_status.value}.", "order", order.id, f"order-item:{item.id}:{new_status.value}:customer")
        items = (await db.execute(select(OrderItem).where(OrderItem.order_id == order.id).with_for_update())).scalars().all()
        await _sync_order(order, items); await db.commit(); await db.refresh(item); return item
    except Exception:
        await db.rollback(); raise
