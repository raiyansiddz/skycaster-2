from fastapi import APIRouter

from app.api.v1 import auth, users, api_keys, subscriptions, weather, billing, usage, admin, support

api_router = APIRouter()

# Include all routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])  
api_router.include_router(api_keys.router, prefix="/api-keys", tags=["API Keys"])
api_router.include_router(subscriptions.router, prefix="/subscriptions", tags=["Subscriptions"])
api_router.include_router(weather.router, prefix="/weather", tags=["Weather API"])
api_router.include_router(billing.router, prefix="/billing", tags=["Billing"])
api_router.include_router(usage.router, prefix="/usage", tags=["Usage & Analytics"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(support.router, prefix="/support", tags=["Support"])