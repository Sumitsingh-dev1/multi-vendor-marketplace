import jwt



from app.core.config import settings
from datetime import datetime, timedelta, timezone


def create_access_token(data: dict) -> str:
    to_encode = data.copy()

    now = datetime.now(timezone.utc)

    expire = now + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({
        "iat": now,
        "exp": expire
    })

    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        settings.algorithm
       
    )
def decode_access_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        settings.algorithm
        
    )