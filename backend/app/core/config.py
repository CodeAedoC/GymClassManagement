from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "Gym & Fitness Facility Membership Portal"
    ENVIRONMENT: str = "development"
    DATABASE_URL: str = "postgresql+psycopg://gym_user:gym_password@localhost:5432/gym_db"
    REDIS_URL: str = "redis://localhost:6379/0"
    
    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
