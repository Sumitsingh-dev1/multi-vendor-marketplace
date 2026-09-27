from pydantic import BaseModel, ConfigDict, EmailStr


from app.models.customer import UserRole


class CustomerCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: str
    role: UserRole = UserRole.CUSTOMER

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
