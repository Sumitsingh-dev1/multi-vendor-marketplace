from datetime import datetime, timedelta, timezone
import secrets

from fastapi import HTTPException
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.core.security import hash_password, verify_password
from app.models.customer import Customer
from app.models.password_reset_token import PasswordResetToken
from app.services.email import send_password_reset_otp

def reset_password(
    db: Session,
    email: str,
    otp: str,
    new_password: str
):
    # 1. Find the customer
    customer = db.query(Customer).filter(
        Customer.email == email
    ).first()

    if not customer:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired OTP"
        )

    # 2. Get the newest unused reset token
    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.customer_id == customer.id,
        PasswordResetToken.used == False
    ).order_by(
        PasswordResetToken.created_at.desc()
    ).first()

    if not reset_token:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired OTP"
        )

    # 3. Check expiry
    if reset_token.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired OTP"
        )

    # 4. Verify OTP
    if not verify_password(
        otp,
        reset_token.token_hash
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired OTP"
        )

    # 5. Change password + invalidate OTP
    try:
        customer.password_hash = hash_password(new_password)

        customer.password_changed_at = datetime.now(
            timezone.utc
        )

        reset_token.used = True

        db.commit()
        db.refresh(customer)

    except Exception:
        db.rollback()
        raise

    return {
        "message": "Password reset successfully"
    }



RESET_OTP_MINUTES = 15


def create_password_reset_otp(
    db: Session,
    email: str
):
    # Find customer by email
    customer = db.query(Customer).filter(
        Customer.email == email
    ).first()

    # Don't reveal whether the email exists
    if not customer:
        return None

    # Invalidate previous unused OTPs
    db.query(PasswordResetToken).filter(
        PasswordResetToken.customer_id == customer.id,
        PasswordResetToken.used == False
    ).update(
        {"used": True},
        synchronize_session=False
    )

    # Generate 6-digit OTP
    otp = f"{secrets.randbelow(1_000_000):06d}"

    # Hash OTP before storing it
    otp_hash = hash_password(otp)

    # 15-minute expiry
    expires_at = (
        datetime.now(timezone.utc)
        + timedelta(minutes=RESET_OTP_MINUTES)
    )

    reset_token = PasswordResetToken(
        customer_id=customer.id,
        token_hash=otp_hash,
        expires_at=expires_at,
        used=False
    )

    try:
        db.add(reset_token)
        db.commit()
        db.refresh(reset_token)

        send_password_reset_otp(
    customer.email,
    otp
)
        
    except Exception:
        db.rollback()
        raise

    return {
        "customer": customer,
        "otp": otp
    }