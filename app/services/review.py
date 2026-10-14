from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderItemStatus
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.review import Review
from app.models.seller_product import SellerProduct


async def create_review(db: AsyncSession, customer_id: int, product_id: int, order_item_id: int, rating: int, comment: str | None) -> Review:
    try:
        product = (await db.execute(select(Product).where(Product.id == product_id))).scalar_one_or_none()
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        item = (await db.execute(
            select(OrderItem).join(Order, Order.id == OrderItem.order_id).join(
                SellerProduct, SellerProduct.id == OrderItem.seller_product_id
            ).where(
                OrderItem.id == order_item_id,
                Order.customer_id == customer_id,
                SellerProduct.product_id == product_id,
                OrderItem.status == OrderItemStatus.DELIVERED,
            ).with_for_update()
        )).scalar_one_or_none()
        if item is None:
            raise HTTPException(status_code=403, detail="A delivered purchase of this product is required")
        existing = (await db.execute(select(Review).where(Review.order_item_id == item.id).with_for_update())).scalar_one_or_none()
        if existing is not None:
            raise HTTPException(status_code=409, detail="This purchase has already been reviewed")
        review = Review(product_id=product_id, customer_id=customer_id, order_item_id=item.id, rating=rating, comment=comment)
        db.add(review)
        await db.commit()
        await db.refresh(review)
        return review
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="This purchase has already been reviewed")
    except Exception:
        await db.rollback()
        raise


async def list_product_reviews(db: AsyncSession, product_id: int, limit: int, offset: int):
    rows = (await db.execute(select(Review).where(Review.product_id == product_id, Review.is_hidden.is_(False)).order_by(Review.created_at.desc(), Review.id.desc()).limit(limit + 1).offset(offset))).scalars().all()
    return rows[:limit], len(rows) > limit


async def list_customer_reviews(db: AsyncSession, customer_id: int, limit: int, offset: int):
    rows = (await db.execute(select(Review).where(Review.customer_id == customer_id).order_by(Review.created_at.desc(), Review.id.desc()).limit(limit + 1).offset(offset))).scalars().all()
    return rows[:limit], len(rows) > limit


async def update_review(db: AsyncSession, review_id: int, customer_id: int, rating: int | None, comment: str | None, update_comment: bool) -> Review:
    review = (await db.execute(select(Review).where(Review.id == review_id, Review.customer_id == customer_id).with_for_update())).scalar_one_or_none()
    if review is None: raise HTTPException(status_code=404, detail="Review not found")
    if rating is not None: review.rating = rating
    if update_comment: review.comment = comment
    await db.commit(); await db.refresh(review)
    return review


async def delete_review(db: AsyncSession, review_id: int, customer_id: int) -> None:
    review = (await db.execute(select(Review).where(Review.id == review_id, Review.customer_id == customer_id).with_for_update())).scalar_one_or_none()
    if review is None: raise HTTPException(status_code=404, detail="Review not found")
    await db.delete(review); await db.commit()


async def set_review_visibility(db: AsyncSession, review_id: int, is_hidden: bool) -> Review:
    review = (await db.execute(select(Review).where(Review.id == review_id).with_for_update())).scalar_one_or_none()
    if review is None: raise HTTPException(status_code=404, detail="Review not found")
    review.is_hidden = is_hidden
    await db.commit(); await db.refresh(review)
    return review
