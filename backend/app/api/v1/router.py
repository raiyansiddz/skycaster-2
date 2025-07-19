from fastapi import APIRouter

from app.api.v1 import auth, users, api_keys, subscriptions, billing, usage, admin, support, skycaster_weather, audit_analytics

api_router = APIRouter()

# Include all routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])  
api_router.include_router(api_keys.router, prefix="/api-keys", tags=["API Keys"])
api_router.include_router(subscriptions.router, prefix="/subscriptions", tags=["Subscriptions"])

# New Skycaster Weather API (replaces old weather.router)
api_router.include_router(skycaster_weather.router, prefix="/weather", tags=["Skycaster Weather API"])

# Legacy weather router removed - weather module no longer available

api_router.include_router(billing.router, prefix="/billing", tags=["Billing"])
api_router.include_router(usage.router, prefix="/usage", tags=["Usage & Analytics"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(support.router, prefix="/support", tags=["Support"])

# Advanced Audit Analytics
api_router.include_router(audit_analytics.router, prefix="/audit", tags=["Audit Analytics"])