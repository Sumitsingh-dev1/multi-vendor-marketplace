from fastapi import FastAPI
from sqlalchemy import text

from app.core.config import settings
from app.database import engine


app = FastAPI(
    title="Multi-Vendor Marketplace API",
    version="1.0.0"
)


@app.get("/")
def home():
    return {
        "message": "Marketplace API is running"
    }


@app.get("/db-test")
def db_test():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))

        return {
            "database": result.scalar()
        }