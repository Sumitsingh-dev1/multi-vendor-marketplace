from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY : str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    algorithm: str 

    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASSWORD: str
    SMTP_FROM: str
    

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()