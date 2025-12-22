import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours (1440 minutes)
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 14  # 14 days
    ALGORITHM: str = "HS256"
    JWT_SECRET_KEY: str = os.getenv('JWT_SECRET_KEY')  # should be kept secret
    JWT_REFRESH_SECRET_KEY: str = os.getenv('JWT_REFRESH_SECRET_KEY')  # should be kept secret

settings = Settings()
