from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    
    # Redis
    REDIS_URL: str
    
    # JWT
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # Twilio
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_PHONE_NUMBER: str
    TWILIO_WHATSAPP_NUMBER: Optional[str] = None
    
    # MinIO/S3
    MINIO_ENDPOINT: str
    MINIO_ROOT_USER: str
    MINIO_ROOT_PASSWORD: str
    MINIO_BUCKET: str = "exhibidores"
    MINIO_USE_SSL: bool = False
    
    # App
    APP_NAME: str = "Sistema de Exhibidores"
    FRONTEND_URL: str = "http://localhost:3001"
    BACKEND_URL: str = "http://localhost:8001"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    
    # Security
    RATE_LIMIT_PER_MINUTE: int = 60
    OTP_EXPIRE_MINUTES: int = 5
    MAX_OTP_ATTEMPTS: int = 3
    MAX_OTP_PER_HOUR: int = 3
    MAX_OTP_PER_DAY_IP: int = 10
    ALLOWED_ORIGINS: str = "http://localhost:3001,http://localhost:3000,http://localhost:5173"
    
    # Retention
    DATA_RETENTION_DAYS: int = 365
    
    # Booking
    DEFAULT_BOOKING_WEEKS: int = 2
    MAX_BOOKING_WEEKS: int = 4
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
