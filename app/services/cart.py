from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.product import Product
from app.models.seller_product import SellerProduct


async def add_item_to_cart(
    db: AsyncSession,
    customer_id: int,
    seller_product_id: int,
    quantity: int,
):
    result = await db.execute(
        select(SellerProduct).where(
            SellerProduct.id == seller_product_id
        )
    )
    seller_product = result.scalar_one_or_none()

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

    if quantity > seller_product.stock:
        raise HTTPException(
            status_code=400,
            detail="Not enough stock",
        )

    result = await db.execute(
        select(Cart).where(
            Cart.customer_id == customer_id
        )
    )
    cart = result.scalar_one_or_none()

    if cart is None:
        cart = Cart(
            customer_id=customer_id
        )
        db.add(cart)
        await db.flush()

    result = await db.execute(
        select(CartItem).where(
            CartItem.cart_id == cart.id,
            CartItem.seller_product_id == seller_product_id,
        )
    )
    cart_item = result.scalar_one_or_none()

    if cart_item is not None:
        new_quantity = (
            cart_item.quantity + quantity
        )

        if new_quantity > seller_product.stock:
            raise HTTPException(
                status_code=400,
                detail="Not enough stock",
            )

        cart_item.quantity = new_quantity

    else:
        cart_item = CartItem(
            cart_id=cart.id,
            seller_product_id=seller_product_id,
            quantity=quantity,
        )

        db.add(cart_item)

    await db.commit()

    return cart_item


async def get_customer_cart(
    db: AsyncSession,
    customer_id: int,
):
    result = await db.execute(
        select(Cart).where(
            Cart.customer_id == customer_id
        )
    )
    cart = result.scalar_one_or_none()

    if cart is None:
        return None, []

    statement = (
        select(CartItem, SellerProduct, Product)
        .join(
            SellerProduct,
            SellerProduct.id == CartItem.seller_product_id,
        )
        .join(
            Product,
            Product.id == SellerProduct.product_id,
        )
        .where(
            CartItem.cart_id == cart.id
        )
    )

    result = await db.execute(statement)
    rows = result.all()

    return cart.id, rows


async def update_cart_item(
    db: AsyncSession,
    customer_id: int,
    cart_item_id: int,
    quantity: int,
):
    result = await db.execute(
        select(CartItem)
        .join(Cart)
        .where(
            CartItem.id == cart_item_id,
            Cart.customer_id == customer_id,
        )
    )
    cart_item = result.scalar_one_or_none()

    if cart_item is None:
        raise HTTPException(
            status_code=404,
            detail="Cart item not found",
        )

    result = await db.execute(
        select(SellerProduct).where(
            SellerProduct.id == cart_item.seller_product_id
        )
    )
    seller_product = result.scalar_one_or_none()

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

    if quantity > seller_product.stock:
        raise HTTPException(
            status_code=400,
            detail="Not enough stock",
        )

    cart_item.quantity = quantity

    await db.commit()
    await db.refresh(cart_item)

    return cart_item


async def delete_cart_item(
    db: AsyncSession,
    customer_id: int,
    cart_item_id: int,
):
    result = await db.execute(
        select(CartItem)
        .join(Cart)
        .where(
            CartItem.id == cart_item_id,
            Cart.customer_id == customer_id,
        )
    )
    cart_item = result.scalar_one_or_none()

    if cart_item is None:
        raise HTTPException(
            status_code=404,
            detail="Cart item not found",
        )

    await db.delete(cart_item)
    await db.commit()
