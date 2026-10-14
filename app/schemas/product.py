from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    name: str
    description: str | None = None
    category_id: int


class ProductResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    category_id: int

    model_config = ConfigDict(from_attributes=True)


class SellerListingCreate(BaseModel):
    name: str
    description: str | None = None
    category_id: int
    price: float
    stock: int
    sku: str


class ProductImageResponse(BaseModel):
    id: int
    product_id: int
    image_url: str
    is_primary: bool
    sort_order: int

    model_config = ConfigDict(from_attributes=True)


class ProductListingResponse(BaseModel):
    product_id: int
    name: str
    description: str | None = None
    category_id: int
    seller_id: int
    price: float
    stock: int
    sku: str
    images: list[ProductImageResponse] = Field(
        default_factory=list
    )
    average_rating: float | None = None
    review_count: int = 0


class ProductListResponse(BaseModel):
    items: list[ProductListingResponse]
    limit: int
    offset: int
    has_next: bool
