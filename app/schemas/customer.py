from pydantic import BaseModel, ConfigDict, EmailStr, Field


from app.models.customer import UserRole
from app.core.config import settings


class CustomerCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    email: EmailStr
    password: str = Field(min_length=settings.PASSWORD_MIN_LENGTH)
    phone: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
