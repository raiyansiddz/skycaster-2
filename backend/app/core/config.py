import os
from pydantic import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/skycaster_db")
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-jwt-secret-key-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Stripe
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    
    # Weather API
    WEATHER_API_KEY: str = os.getenv("WEATHER_API_KEY", "08e9d66860b74ffaa1c184858251407")
    WEATHER_API_BASE_URL: str = os.getenv("WEATHER_API_BASE_URL", "https://api.weatherapi.com/v1")
    
    # Sentry
    SENTRY_DSN: Optional[str] = os.getenv("SENTRY_DSN")
    
    # Email
    SMTP_HOST: str = os.getenv("SMTP_HOST", "localhost")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "noreply@skycaster.com")
    
    # Admin
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@skycaster.com")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin123")
    
    # Celery
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379")
    
    # Rate Limiting
    RATE_LIMITS = {
        "free": {"requests_per_minute": 60, "requests_per_month": 5000},
        "developer": {"requests_per_minute": 600, "requests_per_month": 50000},
        "business": {"requests_per_minute": 1800, "requests_per_month": 200000},
        "enterprise": {"requests_per_minute": 6000, "requests_per_month": 1000000}
    }
    
    # Subscription Plans
    SUBSCRIPTION_PLANS = {
        "free": {"name": "Free", "price": 0, "stripe_price_id": ""},
        "developer": {"name": "Developer", "price": 999, "stripe_price_id": "price_developer"},
        "business": {"name": "Business", "price": 3999, "stripe_price_id": "price_business"},
        "enterprise": {"name": "Enterprise", "price": 9999, "stripe_price_id": "price_enterprise"}
    }
    
    class Config:
        env_file = ".env"

settings = Settings()