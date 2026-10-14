from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


def make_async_database_url(database_url: str) -> str:
    url = make_url(database_url)
    if url.drivername.startswith("postgresql"):
        url = url.set(drivername="postgresql+asyncpg")
    return url.render_as_string(hide_password=False)


ASYNC_DATABASE_URL = make_async_database_url(settings.DATABASE_URL)

async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass
