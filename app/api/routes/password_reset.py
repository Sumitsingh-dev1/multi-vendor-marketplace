from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_async_db
from app.schemas.password_reset import (
    ForgotPasswordRequest,
    ResetPasswordRequest
)
from app.services.password_reset import (
    create_password_reset_otp,
    reset_password
)


router = APIRouter(
    prefix="/auth",
    tags=["Password Reset"]
)


@router.post("/forgot-password")
async def forgot_password(
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_async_db),
):
    await create_password_reset_otp(
        db=db,
        email=data.email
    )

    return {
        "message": (
            "If an account exists for this email, "
            "a password reset OTP has been sent."
        )
    }


@router.post("/reset-password")
async def reset_password_endpoint(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_async_db),
):
    return await reset_password(
        db=db,
        email=data.email,
        otp=data.otp,
        new_password=data.new_password
    )
