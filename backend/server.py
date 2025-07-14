from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import jwt
import bcrypt
import redis.asyncio as redis
import json
import time
from weather_providers.weatherapi import WeatherAPIProvider
from weather_providers.base import WeatherResponse

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Configuration
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']
JWT_SECRET = os.environ['JWT_SECRET']
REDIS_URL = os.environ['REDIS_URL']
WEATHER_API_KEY = os.environ['WEATHER_API_KEY']
WEATHER_API_BASE_URL = os.environ['WEATHER_API_BASE_URL']

# Initialize connections
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]
redis_client = redis.from_url(REDIS_URL)

# Initialize weather provider
weather_provider = WeatherAPIProvider(WEATHER_API_KEY, WEATHER_API_BASE_URL)

# Create FastAPI app
app = FastAPI(title="SKYCASTER API", version="1.0.0")
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    password_hash: str
    is_admin: bool = False
    subscription_tier: str = "free"  # free, developer, business, enterprise
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True

class UserCreate(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class ApiKey(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    key: str
    name: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None

class ApiKeyCreate(BaseModel):
    name: str

class UsageLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    api_key_id: str
    endpoint: str
    request_params: Dict[str, Any]
    response_status: int
    response_time: float
    usage_cost: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class SubscriptionTier(BaseModel):
    name: str
    requests_per_minute: int
    requests_per_month: int
    price_monthly: float

# Subscription tiers
SUBSCRIPTION_TIERS = {
    "free": SubscriptionTier(name="Free", requests_per_minute=60, requests_per_month=5000, price_monthly=0.0),
    "developer": SubscriptionTier(name="Developer", requests_per_minute=600, requests_per_month=50000, price_monthly=999.0),
    "business": SubscriptionTier(name="Business", requests_per_minute=1800, requests_per_month=200000, price_monthly=3999.0),
    "enterprise": SubscriptionTier(name="Enterprise", requests_per_minute=6000, requests_per_month=1000000, price_monthly=9999.0)
}

# Helper functions
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_jwt_token(user_id: str) -> str:
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def verify_jwt_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload.get("user_id")
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    user_id = verify_jwt_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_dict = await db.users.find_one({"id": user_id})
    if not user_dict:
        raise HTTPException(status_code=404, detail="User not found")
    
    return User(**user_dict)

async def get_user_by_api_key(api_key: str) -> Optional[User]:
    api_key_doc = await db.api_keys.find_one({"key": api_key, "is_active": True})
    if not api_key_doc:
        return None
    
    user_dict = await db.users.find_one({"id": api_key_doc["user_id"], "is_active": True})
    if not user_dict:
        return None
    
    return User(**user_dict), ApiKey(**api_key_doc)

async def check_rate_limit(user_id: str, api_key_id: str, tier: str) -> bool:
    """Check if user has exceeded rate limits"""
    tier_info = SUBSCRIPTION_TIERS[tier]
    
    # Check per-minute limit
    minute_key = f"rate_limit:minute:{user_id}:{int(time.time() // 60)}"
    minute_count = await redis_client.get(minute_key)
    minute_count = int(minute_count) if minute_count else 0
    
    if minute_count >= tier_info.requests_per_minute:
        return False
    
    # Check monthly limit
    month_key = f"rate_limit:month:{user_id}:{datetime.utcnow().strftime('%Y-%m')}"
    month_count = await redis_client.get(month_key)
    month_count = int(month_count) if month_count else 0
    
    if month_count >= tier_info.requests_per_month:
        return False
    
    # Increment counters
    await redis_client.incr(minute_key)
    await redis_client.expire(minute_key, 60)
    await redis_client.incr(month_key)
    await redis_client.expire(month_key, 30 * 24 * 60 * 60)  # 30 days
    
    return True

async def log_usage(user_id: str, api_key_id: str, endpoint: str, params: Dict, status: int, response_time: float, cost: float):
    """Log API usage for billing and analytics"""
    usage_log = UsageLog(
        user_id=user_id,
        api_key_id=api_key_id,
        endpoint=endpoint,
        request_params=params,
        response_status=status,
        response_time=response_time,
        usage_cost=cost
    )
    await db.usage_logs.insert_one(usage_log.dict())

async def require_api_key(x_api_key: str = Header(...)):
    """Middleware to require API key for weather endpoints"""
    result = await get_user_by_api_key(x_api_key)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    user, api_key = result
    
    # Check rate limits
    if not await check_rate_limit(user.id, api_key.id, user.subscription_tier):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    return user, api_key

# Auth routes
@api_router.post("/auth/register")
async def register(user_data: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password)
    )
    await db.users.insert_one(user.dict())
    
    # Create default API key
    api_key = ApiKey(
        user_id=user.id,
        key=f"sk_{str(uuid.uuid4()).replace('-', '')}",
        name="Default Key"
    )
    await db.api_keys.insert_one(api_key.dict())
    
    token = create_jwt_token(user.id)
    
    return {
        "message": "User registered successfully",
        "token": token,
        "user": {"id": user.id, "email": user.email, "subscription_tier": user.subscription_tier},
        "api_key": {"id": api_key.id, "key": api_key.key, "name": api_key.name}
    }

@api_router.post("/auth/login")
async def login(user_data: UserLogin):
    user_dict = await db.users.find_one({"email": user_data.email})
    if not user_dict or not verify_password(user_data.password, user_dict["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user = User(**user_dict)
    token = create_jwt_token(user.id)
    
    return {
        "message": "Login successful",
        "token": token,
        "user": {"id": user.id, "email": user.email, "subscription_tier": user.subscription_tier}
    }

# API Key management
@api_router.get("/api-keys")
async def get_api_keys(current_user: User = Depends(get_current_user)):
    api_keys = await db.api_keys.find({"user_id": current_user.id, "is_active": True}).to_list(100)
    return [{"id": key["id"], "name": key["name"], "key": key["key"][:8] + "..." + key["key"][-4:], "created_at": key["created_at"]} for key in api_keys]

@api_router.post("/api-keys")
async def create_api_key(key_data: ApiKeyCreate, current_user: User = Depends(get_current_user)):
    api_key = ApiKey(
        user_id=current_user.id,
        key=f"sk_{str(uuid.uuid4()).replace('-', '')}",
        name=key_data.name
    )
    await db.api_keys.insert_one(api_key.dict())
    
    return {
        "message": "API key created successfully",
        "api_key": {"id": api_key.id, "key": api_key.key, "name": api_key.name}
    }

@api_router.delete("/api-keys/{key_id}")
async def delete_api_key(key_id: str, current_user: User = Depends(get_current_user)):
    result = await db.api_keys.update_one(
        {"id": key_id, "user_id": current_user.id},
        {"$set": {"is_active": False}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="API key not found")
    
    return {"message": "API key deleted successfully"}

# Weather API proxy endpoints
@api_router.get("/weather/current")
async def get_current_weather(location: str, auth_data=Depends(require_api_key)):
    user, api_key = auth_data
    start_time = time.time()
    
    try:
        response = await weather_provider.get_current_weather(location)
        response_time = time.time() - start_time
        
        await log_usage(
            user.id, api_key.id, "/weather/current", 
            {"location": location}, 
            200 if response.success else 500, 
            response_time, response.usage_cost
        )
        
        if response.success:
            return {"success": True, "data": response.data, "provider": response.provider}
        else:
            raise HTTPException(status_code=500, detail=response.error)
    
    except Exception as e:
        response_time = time.time() - start_time
        await log_usage(user.id, api_key.id, "/weather/current", {"location": location}, 500, response_time, 0)
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/weather/forecast")
async def get_forecast(location: str, days: int = 3, auth_data=Depends(require_api_key)):
    user, api_key = auth_data
    start_time = time.time()
    
    try:
        response = await weather_provider.get_forecast(location, days)
        response_time = time.time() - start_time
        
        await log_usage(
            user.id, api_key.id, "/weather/forecast", 
            {"location": location, "days": days}, 
            200 if response.success else 500, 
            response_time, response.usage_cost
        )
        
        if response.success:
            return {"success": True, "data": response.data, "provider": response.provider}
        else:
            raise HTTPException(status_code=500, detail=response.error)
    
    except Exception as e:
        response_time = time.time() - start_time
        await log_usage(user.id, api_key.id, "/weather/forecast", {"location": location, "days": days}, 500, response_time, 0)
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/weather/history")
async def get_history(location: str, date: str, auth_data=Depends(require_api_key)):
    user, api_key = auth_data
    start_time = time.time()
    
    try:
        response = await weather_provider.get_history(location, date)
        response_time = time.time() - start_time
        
        await log_usage(
            user.id, api_key.id, "/weather/history", 
            {"location": location, "date": date}, 
            200 if response.success else 500, 
            response_time, response.usage_cost
        )
        
        if response.success:
            return {"success": True, "data": response.data, "provider": response.provider}
        else:
            raise HTTPException(status_code=500, detail=response.error)
    
    except Exception as e:
        response_time = time.time() - start_time
        await log_usage(user.id, api_key.id, "/weather/history", {"location": location, "date": date}, 500, response_time, 0)
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/weather/search")
async def search_locations(query: str, auth_data=Depends(require_api_key)):
    user, api_key = auth_data
    start_time = time.time()
    
    try:
        response = await weather_provider.search_locations(query)
        response_time = time.time() - start_time
        
        await log_usage(
            user.id, api_key.id, "/weather/search", 
            {"query": query}, 
            200 if response.success else 500, 
            response_time, response.usage_cost
        )
        
        if response.success:
            return {"success": True, "data": response.data, "provider": response.provider}
        else:
            raise HTTPException(status_code=500, detail=response.error)
    
    except Exception as e:
        response_time = time.time() - start_time
        await log_usage(user.id, api_key.id, "/weather/search", {"query": query}, 500, response_time, 0)
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/weather/astronomy")
async def get_astronomy(location: str, date: str, auth_data=Depends(require_api_key)):
    user, api_key = auth_data
    start_time = time.time()
    
    try:
        response = await weather_provider.get_astronomy(location, date)
        response_time = time.time() - start_time
        
        await log_usage(
            user.id, api_key.id, "/weather/astronomy", 
            {"location": location, "date": date}, 
            200 if response.success else 500, 
            response_time, response.usage_cost
        )
        
        if response.success:
            return {"success": True, "data": response.data, "provider": response.provider}
        else:
            raise HTTPException(status_code=500, detail=response.error)
    
    except Exception as e:
        response_time = time.time() - start_time
        await log_usage(user.id, api_key.id, "/weather/astronomy", {"location": location, "date": date}, 500, response_time, 0)
        raise HTTPException(status_code=500, detail=str(e))

# Usage and analytics
@api_router.get("/usage")
async def get_usage(current_user: User = Depends(get_current_user)):
    # Get usage statistics
    usage_logs = await db.usage_logs.find({"user_id": current_user.id}).to_list(1000)
    
    total_requests = len(usage_logs)
    successful_requests = len([log for log in usage_logs if log["response_status"] == 200])
    total_cost = sum(log["usage_cost"] for log in usage_logs)
    
    # Get current month usage
    current_month = datetime.utcnow().strftime('%Y-%m')
    month_key = f"rate_limit:month:{current_user.id}:{current_month}"
    month_usage = await redis_client.get(month_key)
    month_usage = int(month_usage) if month_usage else 0
    
    tier_info = SUBSCRIPTION_TIERS[current_user.subscription_tier]
    
    return {
        "user_id": current_user.id,
        "subscription_tier": current_user.subscription_tier,
        "current_month_usage": month_usage,
        "monthly_limit": tier_info.requests_per_month,
        "usage_percentage": (month_usage / tier_info.requests_per_month) * 100,
        "total_requests": total_requests,
        "successful_requests": successful_requests,
        "total_cost": total_cost,
        "rate_limit_per_minute": tier_info.requests_per_minute
    }

@api_router.get("/subscription-tiers")
async def get_subscription_tiers():
    return {
        "tiers": [
            {
                "name": tier.name,
                "key": key,
                "requests_per_minute": tier.requests_per_minute,
                "requests_per_month": tier.requests_per_month,
                "price_monthly": tier.price_monthly
            }
            for key, tier in SUBSCRIPTION_TIERS.items()
        ]
    }

# Health check
@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

# Include the router in the main app
app.include_router(api_router)

@app.on_event("shutdown")
async def shutdown_event():
    client.close()
    await redis_client.close()
    await weather_provider.close()