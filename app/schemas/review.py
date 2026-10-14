from datetime import datetime
from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    order_item_id: int = Field(gt=0)
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


class ReviewUpdate(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


class ReviewVisibilityUpdate(BaseModel):
    is_hidden: bool


class ReviewResponse(BaseModel):
    id: int
    product_id: int
    rating: int
    comment: str | None
    is_hidden: bool
    created_at: datetime
    updated_at: datetime


class ReviewListResponse(BaseModel):
    items: list[ReviewResponse]
    limit: int
    offset: int
    has_next: bool
