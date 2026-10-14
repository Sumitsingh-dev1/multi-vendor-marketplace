from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_async_db, get_current_customer, require_admin
from app.models.customer import Customer
from app.models.product import Product
from app.schemas.review import ReviewCreate, ReviewListResponse, ReviewResponse, ReviewUpdate, ReviewVisibilityUpdate
from app.services.review import create_review, delete_review, list_customer_reviews, list_product_reviews, set_review_visibility, update_review

router = APIRouter(tags=["Reviews"])


def response(review):
    return ReviewResponse(id=review.id, product_id=review.product_id, rating=review.rating, comment=review.comment, is_hidden=review.is_hidden, created_at=review.created_at, updated_at=review.updated_at)


@router.post("/products/{product_id}/reviews", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def submit_review(product_id: int, data: ReviewCreate, customer: Customer = Depends(get_current_customer), db: AsyncSession = Depends(get_async_db)):
    return response(await create_review(db, customer.id, product_id, data.order_item_id, data.rating, data.comment))


@router.get("/products/{product_id}/reviews", response_model=ReviewListResponse)
async def product_reviews(product_id: int, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0), db: AsyncSession = Depends(get_async_db)):
    if (await db.execute(select(Product.id).where(Product.id == product_id))).scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Product not found")
    reviews, has_next = await list_product_reviews(db, product_id, limit, offset)
    return ReviewListResponse(items=[response(review) for review in reviews], limit=limit, offset=offset, has_next=has_next)


@router.get("/reviews/me", response_model=ReviewListResponse)
async def my_reviews(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0), customer: Customer = Depends(get_current_customer), db: AsyncSession = Depends(get_async_db)):
    reviews, has_next = await list_customer_reviews(db, customer.id, limit, offset)
    return ReviewListResponse(items=[response(review) for review in reviews], limit=limit, offset=offset, has_next=has_next)


@router.patch("/reviews/{review_id}", response_model=ReviewResponse)
async def edit_review(review_id: int, data: ReviewUpdate, customer: Customer = Depends(get_current_customer), db: AsyncSession = Depends(get_async_db)):
    if not data.model_fields_set:
        raise HTTPException(status_code=400, detail="Provide a rating or comment to update")
    return response(await update_review(db, review_id, customer.id, data.rating, data.comment, "comment" in data.model_fields_set))


@router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_review(review_id: int, customer: Customer = Depends(get_current_customer), db: AsyncSession = Depends(get_async_db)):
    await delete_review(db, review_id, customer.id)


@router.patch("/admin/reviews/{review_id}/visibility", response_model=ReviewResponse)
async def moderate_review(review_id: int, data: ReviewVisibilityUpdate, admin: Customer = Depends(require_admin), db: AsyncSession = Depends(get_async_db)):
    return response(await set_review_visibility(db, review_id, data.is_hidden))
