import redis
import time
from typing import Optional, Tuple
from datetime import datetime, timedelta
import logging

from app.core.config import settings
from app.models.subscription import SubscriptionPlan

logger = logging.getLogger(__name__)

class RateLimitService:
    def __init__(self):
        try:
            self.redis_client = redis.from_url(settings.REDIS_URL)
            # Test the connection
            self.redis_client.ping()
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            self.redis_client = None
    
    def check_rate_limit(self, api_key: str, plan: SubscriptionPlan) -> Tuple[bool, dict]:
        """
        Check if API key has exceeded rate limits
        Returns (is_allowed, limit_info)
        """
        limits = settings.RATE_LIMITS.get(plan.value, settings.RATE_LIMITS["free"])
        
        # Check minute rate limit
        minute_key = f"rate_limit:minute:{api_key}:{int(time.time() // 60)}"
        minute_requests = self.redis_client.get(minute_key)
        minute_requests = int(minute_requests) if minute_requests else 0
        
        if minute_requests >= limits["requests_per_minute"]:
            return False, {
                "limit_type": "minute",
                "limit": limits["requests_per_minute"],
                "current": minute_requests,
                "reset_time": int(time.time() // 60 + 1) * 60
            }
        
        # Check monthly rate limit
        current_month = datetime.utcnow().strftime("%Y-%m")
        month_key = f"rate_limit:month:{api_key}:{current_month}"
        month_requests = self.redis_client.get(month_key)
        month_requests = int(month_requests) if month_requests else 0
        
        if month_requests >= limits["requests_per_month"]:
            # Calculate next month's timestamp
            next_month = (datetime.utcnow().replace(day=1) + timedelta(days=32)).replace(day=1)
            return False, {
                "limit_type": "month",
                "limit": limits["requests_per_month"],
                "current": month_requests,
                "reset_time": int(next_month.timestamp())
            }
        
        # Increment counters
        self.redis_client.incr(minute_key)
        self.redis_client.expire(minute_key, 60)
        
        self.redis_client.incr(month_key)
        # Set expiry for end of month
        next_month = (datetime.utcnow().replace(day=1) + timedelta(days=32)).replace(day=1)
        self.redis_client.expireat(month_key, int(next_month.timestamp()))
        
        return True, {
            "limit_type": "none",
            "minute_limit": limits["requests_per_minute"],
            "month_limit": limits["requests_per_month"],
            "minute_remaining": limits["requests_per_minute"] - minute_requests - 1,
            "month_remaining": limits["requests_per_month"] - month_requests - 1
        }
    
    def get_rate_limit_info(self, api_key: str, plan: SubscriptionPlan) -> dict:
        """Get current rate limit information without incrementing counters"""
        limits = settings.RATE_LIMITS.get(plan.value, settings.RATE_LIMITS["free"])
        
        # Get current minute usage
        minute_key = f"rate_limit:minute:{api_key}:{int(time.time() // 60)}"
        minute_requests = self.redis_client.get(minute_key)
        minute_requests = int(minute_requests) if minute_requests else 0
        
        # Get current month usage
        current_month = datetime.utcnow().strftime("%Y-%m")
        month_key = f"rate_limit:month:{api_key}:{current_month}"
        month_requests = self.redis_client.get(month_key)
        month_requests = int(month_requests) if month_requests else 0
        
        return {
            "plan": plan.value,
            "minute_limit": limits["requests_per_minute"],
            "month_limit": limits["requests_per_month"],
            "minute_used": minute_requests,
            "month_used": month_requests,
            "minute_remaining": limits["requests_per_minute"] - minute_requests,
            "month_remaining": limits["requests_per_month"] - month_requests
        }
    
    def reset_rate_limit(self, api_key: str) -> bool:
        """Reset rate limits for an API key (admin only)"""
        try:
            # Delete all rate limit keys for this API key
            keys = self.redis_client.keys(f"rate_limit:*:{api_key}:*")
            if keys:
                self.redis_client.delete(*keys)
            return True
        except Exception:
            return False
    
    def get_all_rate_limits(self) -> dict:
        """Get all current rate limits (admin only)"""
        try:
            keys = self.redis_client.keys("rate_limit:*")
            rate_limits = {}
            
            for key in keys:
                key_str = key.decode('utf-8')
                value = self.redis_client.get(key)
                if value:
                    rate_limits[key_str] = int(value)
            
            return rate_limits
        except Exception:
            return {}
    
    def cleanup_expired_keys(self) -> int:
        """Clean up expired rate limit keys"""
        try:
            # This is handled automatically by Redis TTL, but we can do manual cleanup
            keys = self.redis_client.keys("rate_limit:*")
            cleaned = 0
            
            for key in keys:
                ttl = self.redis_client.ttl(key)
                if ttl == -1:  # Key has no expiry
                    # Set appropriate expiry based on key type
                    key_str = key.decode('utf-8')
                    if ":minute:" in key_str:
                        self.redis_client.expire(key, 60)
                    elif ":month:" in key_str:
                        next_month = (datetime.utcnow().replace(day=1) + timedelta(days=32)).replace(day=1)
                        self.redis_client.expireat(key, int(next_month.timestamp()))
                    cleaned += 1
            
            return cleaned
        except Exception:
            return 0