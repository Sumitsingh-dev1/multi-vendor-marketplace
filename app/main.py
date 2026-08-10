from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(
    title="Multi-Vendor Marketplace API",
    version="1.0.0"
)


@app.get("/")
def home():
    return {
        "message": "Marketplace API is running"
    }