from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.services.auth import AuthService
from app.services.api_key import ApiKeyService
from app.services.subscription import SubscriptionService
from app.services.rate_limit import RateLimitService
from app.models.user import User, UserRole
from app.models.api_key import ApiKey
from app.models.subscription import Subscription

security = HTTPBearer(auto_error=False)

def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Get current authenticated user from JWT token"""
    print(f"DEBUG: get_current_user called with credentials: {credentials}")
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Verify token
    payload = AuthService.verify_token(credentials.credentials)
    if payload is None:
        raise credentials_exception
    
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    # Get user from database
    user = AuthService.get_user_by_id(db, user_id)
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive"
        )
    
    return user

async def get_current_user_optional(request: Request, db: Session) -> Optional[User]:
    """Get current user if JWT token is provided (optional) - for middleware use"""
    try:
        authorization = request.headers.get("authorization")
        if not authorization or not authorization.startswith("Bearer "):
            return None
        
        token = authorization.split(" ")[1]
        payload = AuthService.verify_token(token)
        if payload is None:
            return None
        
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        
        user = AuthService.get_user_by_id(db, user_id)
        if user and user.is_active:
            return user
        
    except Exception:
        pass
    
    return None

async def get_api_key_optional(request: Request, db: Session) -> Optional[ApiKey]:
    """Get API key if provided (optional) - for middleware use"""
    try:
        api_key_header = request.headers.get("x-api-key")
        if not api_key_header:
            return None
        
        api_key = ApiKeyService.get_api_key_by_key(db, api_key_header)
        if api_key:
            return api_key
        
    except Exception:
        pass
    
    return None

def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user"
        )
    return current_user

def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current admin user"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

def get_api_key_user(
    db: Session = Depends(get_db),
    x_api_key: str = Header(..., description="API Key for authentication")
) -> tuple[User, ApiKey, Subscription]:
    """Get user from API key and check rate limits"""
    # Get API key
    api_key = ApiKeyService.get_api_key_by_key(db, x_api_key)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    # Get user
    user = AuthService.get_user_by_id(db, api_key.user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive"
        )
    
    # Get subscription
    subscription = SubscriptionService.get_user_subscription(db, user.id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="No active subscription"
        )
    
    # Check rate limits
    rate_limit_service = RateLimitService()
    is_allowed, limit_info = rate_limit_service.check_rate_limit(x_api_key, subscription.plan)
    
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                "X-RateLimit-Limit": str(limit_info.get("limit", 0)),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(limit_info.get("reset_time", 0))
            }
        )
    
    return user, api_key, subscription

def get_optional_current_user(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None)
) -> Optional[User]:
    """Get current user if token is provided (optional)"""
    if not authorization:
        return None
    
    try:
        if not authorization.startswith("Bearer "):
            return None
        
        token = authorization.split(" ")[1]
        payload = AuthService.verify_token(token)
        if payload is None:
            return None
        
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        
        user = AuthService.get_user_by_id(db, user_id)
        if user and user.is_active:
            return user
        
    except Exception:
        pass
    
    return None

# Rate limiting dependency
def check_rate_limit(
    db: Session = Depends(get_db),
    x_api_key: str = Header(..., description="API Key for authentication")
) -> dict:
    """Check rate limit without full authentication"""
    rate_limit_service = RateLimitService()
    
    # Get API key to determine plan
    api_key = ApiKeyService.get_api_key_by_key(db, x_api_key)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    # Get subscription
    subscription = SubscriptionService.get_user_subscription(db, api_key.user_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="No active subscription"
        )
    
    # Check rate limits
    is_allowed, limit_info = rate_limit_service.check_rate_limit(x_api_key, subscription.plan)
    
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                "X-RateLimit-Limit": str(limit_info.get("limit", 0)),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(limit_info.get("reset_time", 0))
            }
        )
    
    return {
        "api_key": api_key,
        "subscription": subscription,
        "limit_info": limit_info
    }