from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db
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
def forgot_password(
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    create_password_reset_otp(
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
def reset_password_endpoint(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    return reset_password(
        db=db,
        email=data.email,
        otp=data.otp,
        new_password=data.new_password
    )