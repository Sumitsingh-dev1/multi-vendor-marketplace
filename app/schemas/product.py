from pydantic import BaseModel, ConfigDict


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


class ProductListingResponse(BaseModel):
    product_id: int
    name: str
    description: str | None = None
    category_id: int
    seller_id: int
    price: float
    stock: int
    sku: str


class ProductListResponse(BaseModel):
    items: list[ProductListingResponse]
    limit: int
    offset: int
    has_next: bool