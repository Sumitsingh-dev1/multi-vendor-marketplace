from pydantic import BaseModel, Field, ConfigDict
from app.models.order import OrderStatus, OrderItemStatus


class OrderResponse(BaseModel):
    order_id: int
    status: str


class CheckoutRequest(BaseModel):
    address_id: int | None = None

    latitude: float | None = None
    longitude: float | None = None

    address_line: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "address_id": 1
            }
        }
    )


class BuyNowRequest(BaseModel):
    seller_product_id: int
    quantity: int = Field(gt=0)

    address_id: int | None = None

    latitude: float | None = None
    longitude: float | None = None

    address_line: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "seller_product_id": 1,
                "quantity": 1,
                "address_id": 1
            }
        }
    )


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderItemStatusUpdate(BaseModel):
    status: OrderItemStatus


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

    delivery_address_line: str
    delivery_city: str
    delivery_state: str
    delivery_postal_code: str
    delivery_latitude: float
    delivery_longitude: float

    items: list[OrderItemResponse]


class SellerOrderItemResponse(BaseModel):
    order_id: int
    order_item_id: int
    product_id: int
    name: str
    quantity: int
    price: float
    status: OrderItemStatus

    delivery_address_line: str
    delivery_city: str
    delivery_state: str
    delivery_postal_code: str
    delivery_latitude: float
    delivery_longitude: float