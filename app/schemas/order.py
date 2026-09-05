from pydantic import BaseModel, Field
from app.models.order import OrderStatus,OrderItemStatus

class OrderResponse(BaseModel):
    order_id: int
    status: str

class BuyNowRequest(BaseModel):
    seller_product_id: int
    quantity: int = Field(gt=0)
class OrderStatusUpdate(BaseModel):
    status: OrderStatus

class OrderListItem(BaseModel):
    order_id: int
    status: str
class OrderItemResponse(BaseModel):
    order_item_id: int
    product_id: int
    name: str
    seller_product_id: int
    quantity: int
    price: float
    status: OrderItemStatus

class OrderDetailResponse(BaseModel):
    order_id: int
    status: str
    items: list[OrderItemResponse]
class SellerOrderItemResponse(BaseModel):
    order_id: int
    order_item_id: int
    product_id: int
    name: str
    quantity: int
    price: float
    status: OrderItemStatus
class OrderItemStatusUpdate(BaseModel):
    status: OrderItemStatus        
