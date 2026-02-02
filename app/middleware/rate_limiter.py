import redis.asyncio as redis
from fastapi import HTTPException, status
from typing import Optional
import time
from app.config import get_settings
from app.auth.models import AuthContext

class RateLimiter:

    def __init__(self):
        self.settings = get_settings()
        self._redis: Optional[redis.Redis] = None

    async def get_redis(self) -> redis.Redis:
        """Get Redis connection"""
        if self._redis is None:
            self._redis = await redis.from_url(
                self.settings.redis_url,
                encoding="utf-8", decode_responses=True
            )
        return self._redis


    async def check_rate_limit(
        self, auth_context: AuthContext, model_name: str, limit: int,
        window: int = 60
    ) -> bool:
        """Check if request is within rate limit

        Args:
            auth_context: Authentication context
            model_name: Model being accessed
            limit: Maximum requests allowed in window
            window: Time window in seconds
        
        Returns:
            True if within limit, raises HTTPException otherwise
        """
        # Create rate limit key
        user_id = auth_context.user_id
        key = f"ratelimit:{model_name}:{user_id}"
        try:
            redis_client = await self.get_redis()
            # Get current count
            current = await redis_client.get(key)
            current_count = int(current) if current else 0
            if current_count >= limit:
                # Get TTL to inform user when they can retry
                ttl = await redis_client.ttl(key)

                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Try again in {ttl} seconds.",
                    headers={
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(time.time()) + ttl),
                        "Retry-After": str(ttl)
                    }
                )
            # Increment counter
            pipe = redis_client.pipeline()
            pipe.incr(key)
            pipe.expire(key, window)
            await pipe.execute()
            remaining = limit - current_count - 1
            return True
        except HTTPException:
            raise
        except Exception as e:
            # Log error but don't block request if Redis is down
            print(f"Rate limit check failed: {e}")
            return True

    async def get_rate_limit_status(
        self, auth_context: AuthContext, model_name: str, limit: int
    ) -> dict:
        """Get current rate limit status for user"""
        user_id = auth_context.user_id
        key = f"ratelimit:{model_name}:{user_id}"
        try:
            redis_client = await self.get_redis()
            current = await redis_client.get(key)
            current_count = int(current) if current else 0
            ttl = await redis_client.ttl(key)
            return {
                "limit": limit,
                "remaining": max(0, limit - current_count),
                "reset": int(time.time()) + max(0, ttl),
                "used": current_count
            }
        except Exception as e:
            print(f"Failed to get rate limit status: {e}")
            return {
                "limit": limit,
                "remaining": limit,
                "reset": int(time.time()) + 60,
                "used": 0
            }

    async def close(self):
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()

_rate_limiter: Optional[RateLimiter] = None

def get_rate_limiter() -> RateLimiter:
    """Get singleton rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter