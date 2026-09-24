from pydantic import BaseModel


class SellerServiceAreaCreate(BaseModel):
    postal_code: str


class SellerServiceAreaResponse(BaseModel):
    id: int
    postal_code: str