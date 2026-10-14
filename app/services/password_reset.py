from datetime import datetime, timedelta, timezone
import secrets
from fastapi import HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import hash_password, verify_password
from app.models.customer import Customer
from app.models.password_reset_token import PasswordResetToken
from app.services.email import send_password_reset_otp

RESET_OTP_MINUTES = 15
RESET_OTP_REQUEST_COOLDOWN_SECONDS = 60
MAX_OTP_VERIFICATION_ATTEMPTS = 5
INVALID_OTP_ERROR = "Invalid or expired OTP"

async def reset_password(db: AsyncSession, email: str, otp: str, new_password: str):
    result = await db.execute(select(Customer).where(Customer.email == email).with_for_update())
    customer = result.scalar_one_or_none()
    if customer is None:
        raise HTTPException(status_code=400, detail=INVALID_OTP_ERROR)
    result = await db.execute(select(PasswordResetToken).where(PasswordResetToken.customer_id == customer.id, PasswordResetToken.used.is_(False)).order_by(PasswordResetToken.created_at.desc()).with_for_update())
    token = result.scalars().first()
    now = datetime.now(timezone.utc)
    if token is None:
        raise HTTPException(status_code=400, detail=INVALID_OTP_ERROR)
    if token.expires_at <= now or token.verification_attempts >= MAX_OTP_VERIFICATION_ATTEMPTS:
        token.used = True
        await db.commit()
        raise HTTPException(status_code=400, detail=INVALID_OTP_ERROR)
    if not await run_in_threadpool(verify_password, otp, token.token_hash):
        token.verification_attempts += 1
        if token.verification_attempts >= MAX_OTP_VERIFICATION_ATTEMPTS:
            token.used = True
        await db.commit()
        raise HTTPException(status_code=400, detail=INVALID_OTP_ERROR)
    try:
        customer.password_hash = await run_in_threadpool(hash_password, new_password)
        customer.password_changed_at = now
        token.used = True
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return {"message": "Password reset successfully"}

async def create_password_reset_otp(db: AsyncSession, email: str):
    # Account locking serializes requests, ensuring only one OTP can be valid.
    result = await db.execute(select(Customer).where(Customer.email == email).with_for_update())
    customer = result.scalar_one_or_none()
    if customer is None or not customer.is_active:
        return None
    now = datetime.now(timezone.utc)
    latest = await db.execute(select(PasswordResetToken).where(PasswordResetToken.customer_id == customer.id).order_by(PasswordResetToken.created_at.desc()).limit(1))
    last_token = latest.scalar_one_or_none()
    if last_token and (now - last_token.created_at).total_seconds() < RESET_OTP_REQUEST_COOLDOWN_SECONDS:
        return None
    otp = f"{secrets.randbelow(1_000_000):06d}"
    token_hash = await run_in_threadpool(hash_password, otp)
    await db.execute(update(PasswordResetToken).where(PasswordResetToken.customer_id == customer.id, PasswordResetToken.used.is_(False)).values(used=True))
    db.add(PasswordResetToken(customer_id=customer.id, token_hash=token_hash, expires_at=now + timedelta(minutes=RESET_OTP_MINUTES), used=False))
    try:
        await db.flush()
        # A delivery failure rolls back both the new token and invalidations.
        await send_password_reset_otp(customer.email, otp)
        await db.commit()
    except Exception:
        await db.rollback()
    return None
