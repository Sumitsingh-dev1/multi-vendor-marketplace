from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.core.config import settings


class DeliveryAgentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    phone: str = Field(min_length=1, max_length=15)
    password: str = Field(min_length=settings.PASSWORD_MIN_LENGTH)
