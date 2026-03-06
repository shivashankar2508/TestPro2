from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    """
    # App
    APP_NAME: str = "TestTrack Pro"
    APP_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    LOG_LEVEL: str = "INFO"
    
    # Environment
    ENV: str = "development"
    
    # Database
    DATABASE_URL: str
    SQL_ECHO: bool = False
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40
    DB_POOL_RECYCLE: int = 3600
    
    # Security
    SECRET_KEY: str = Field(default="your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    BCRYPT_ROUNDS: int = 12
    
    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8001"
    
    # Email
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SENDER_EMAIL: str = ""
    SENDER_PASSWORD: str = ""
    SENDER_NAME: str = "TestTrack Pro"
    FRONTEND_URL: str = "http://localhost:3000"
    
    # OAuth (Optional for now)
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None
    
    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    
    @field_validator('SECRET_KEY')
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        """Validate that SECRET_KEY is set and strong in production"""
        if info.data.get('ENV') == 'production':
            if v == "your-secret-key-change-in-production" or len(v) < 32:
                raise ValueError('SECRET_KEY must be set and at least 32 characters in production')
        return v
    
    @field_validator('LOG_LEVEL')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is valid"""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'LOG_LEVEL must be one of {valid_levels}')
        return v.upper()
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = Settings()

# Validate production settings
if settings.ENV == "production":
    if settings.DATABASE_URL and "sqlite" in settings.DATABASE_URL.lower():
        raise ValueError("SQLite cannot be used in production. Use PostgreSQL or MySQL.")
    logger.warning("Application running in PRODUCTION mode")
    # Hide docs in production
    logger.info("API documentation disabled in production")
else:
    logger.info(f"Application running in {settings.ENV.upper()} mode")
