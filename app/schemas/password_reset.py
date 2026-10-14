from pydantic import BaseModel, EmailStr, Field
from app.core.config import settings


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str = Field(pattern=r"^\d{6}$")
    new_password: str = Field(min_length=settings.PASSWORD_MIN_LENGTH)
