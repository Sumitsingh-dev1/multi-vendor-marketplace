from pydantic import BaseModel, ConfigDict, EmailStr


class CustomerCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ProductCreate(BaseModel):
    name: str
    description: str | None = None
    category_id: int


class SellerProductCreate(BaseModel):
    product_id: int
    price: float
    stock: int
    sku: str


class CategoryCreate(BaseModel):
    name: str
    description: str | None = None


class ProductResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    category_id: int

    model_config = ConfigDict(from_attributes=True)


class SellerProductResponse(BaseModel):
    id: int
    seller_id: int
    product_id: int
    price: float
    stock: int
    sku: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class CategoryResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    is_active: bool

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
class CategoryUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None         
class AdminCategoryResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    is_active: bool    