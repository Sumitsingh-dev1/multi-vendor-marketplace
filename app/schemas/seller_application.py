from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.models.seller_application import SellerApplicationStatus

class SellerApplicationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    business_name: str = Field(min_length=2, max_length=150)
    business_address: str = Field(min_length=5, max_length=2000)
    tax_identifier: str | None = Field(default=None, max_length=100)

class SellerApplicationReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: SellerApplicationStatus
    admin_notes: str | None = Field(default=None, max_length=2000)

class SellerApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    customer_id: int
    business_name: str
    business_address: str
    tax_identifier: str | None
    status: SellerApplicationStatus
    admin_notes: str | None
    reviewed_by_id: int | None
    reviewed_at: datetime | None
    created_at: datetime
