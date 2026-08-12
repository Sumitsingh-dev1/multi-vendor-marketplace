import jwt

from app.core.config import settings


def create_access_token(data: dict) -> str:
    return jwt.encode(
        data,
        settings.SECRET_KEY,
        algorithm="HS256"
    )
def decode_access_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=["HS256"]
    )