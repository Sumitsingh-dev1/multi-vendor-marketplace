from pydantic import BaseModel, Field

class CartItemCreate(BaseModel):
    seller_product_id: int
    quantity: int = Field(gt=0)

class CartItemResponse(BaseModel):
    cart_item_id: int
    seller_product_id: int
    product_id: int
    name: str
    price: float
    quantity: int
class CartResponse(BaseModel):
    cart_id: int
    items: list[CartItemResponse]        
class CartItemUpdate(BaseModel):
    quantity: int = Field(gt=0)    