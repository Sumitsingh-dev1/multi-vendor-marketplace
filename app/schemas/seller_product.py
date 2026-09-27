from pydantic import BaseModel, ConfigDict


class SellerProductCreate(BaseModel):
    product_id: int
    price: float
    stock: int
    sku: str


class SellerProductResponse(BaseModel):
    id: int
    seller_id: int
    product_id: int
    price: float
    stock: int
    sku: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class SellerProductUpdate(BaseModel):
    price: float | None = None
    stock: int | None = None
    sku: str | None = None
    is_active: bool | None = None


class MySellerProductResponse(BaseModel):
    seller_product_id: int
    product_id: int
    name: str
    price: float
    stock: int
    sku: str
    is_active: bool


class MySellerProductListResponse(BaseModel):
    items: list[MySellerProductResponse]
    limit: int
    offset: int
    has_next: bool