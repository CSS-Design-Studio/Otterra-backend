from fastapi import Depends, HTTPException, Request, status
from app.db.redis import get_redis
from app.core.security import get_current_token

def _make_rate_limiter(max_attempts: int, window_seconds: int, prefix: str):
    """
    Factory Function, generating different setting rate limiter dependency
    """

    def rate_limiter(request: Request, redis=Depends(get_redis)):
        # Skip if redis is in downtime
        if redis is None:
            return
        
        user_ip = request.client.host
        key = f"rate_limit:{prefix}:{user_ip}"

        count =  redis.incr(key)

        # Start setting the TTL
        if count == 1:
            redis.expire(key, window_seconds)

        # Restrict for spanning or brute-force behaviour
        if count > max_attempts:
            ttl = redis.ttl(key)
            raise HTTPException(
                status_code = status.HTTP_429_TOO_MANY_REQUESTS,
                detail = f"Too many attempts. Try again in {ttl} seconds."
            )

    return rate_limiter


def _ai_rate_limit(
    max_attempts: int,
    window_seconds: int,
    prefix: str,
):
    """"
    Rate Limiter keyed by user_id instead of IP
    """
    def rate_limiter(
        payload: dict = Depends(get_current_token),
        redis = Depends(get_redis),
    ):
        if redis is None:
            return
        user_id = payload.get("sub", "anonymous")
        key = f"rate_limit:{prefix}:{user_id}"
        count = redis.incr(key)
        if count == 1:
            redis.expire(key, window_seconds)
        if count > max_attempts:
            ttl = redis.ttl(key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many requests. Try again in {ttl} seconds",
            )
    return rate_limiter
    
    



# Different Endpoint for different parameter rate limiter

rate_limit_login = _make_rate_limiter(max_attempts = 5, window_seconds = 900, prefix = "login")
rate_limit_register = _make_rate_limiter(max_attempts = 3, window_seconds = 5400, prefix="register")
rate_limit_ai_chat = _ai_rate_limit(max_attempts=20, window_seconds=7200, prefix="ai_chat")