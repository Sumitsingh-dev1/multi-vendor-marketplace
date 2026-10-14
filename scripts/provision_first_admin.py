"""Provision the first administrator. Run manually after migrations."""
import asyncio
import getpass

from sqlalchemy import select

# Import all relationship targets before SQLAlchemy configures Customer mappers.
import app.models.cart
import app.models.cart_item
import app.models.delivery_assignment
import app.models.password_reset_token
import app.models.seller_application
import app.models.seller_product
from app.core.security import hash_password
from app.core.config import settings
from app.database import AsyncSessionLocal
from app.models.customer import Customer, UserRole


async def main() -> None:
    email = input("Administrator email: ").strip().lower()
    password = getpass.getpass("Administrator password: ")
    confirm = getpass.getpass("Confirm password: ")
    if not email or len(password) < settings.PASSWORD_MIN_LENGTH or password != confirm:
        raise SystemExit(f"Email and matching password of at least {settings.PASSWORD_MIN_LENGTH} characters are required.")
    name = input("Administrator name: ").strip() or "Administrator"
    phone = input("Administrator phone: ").strip()
    if not phone:
        raise SystemExit("Phone is required.")
    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(Customer.id).where(Customer.role == UserRole.ADMIN).limit(1))
        if existing.scalar_one_or_none() is not None:
            raise SystemExit("An administrator already exists; bootstrap refused.")
        duplicate = await db.execute(select(Customer.id).where(Customer.email == email).limit(1))
        if duplicate.scalar_one_or_none() is not None:
            raise SystemExit("An account with that email already exists.")
        db.add(Customer(name=name, email=email, phone=phone, password_hash=hash_password(password), role=UserRole.ADMIN))
        await db.commit()
    print("First administrator provisioned.")


if __name__ == "__main__":
    asyncio.run(main())
