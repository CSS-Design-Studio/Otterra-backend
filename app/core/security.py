import jwt
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.core.config import settings
from app.db.redis import get_redis
import uuid

ALGORITHM = "HS256"
_bearer = HTTPBearer(auto_error=False)


def create_token(sub: str, role: str = "user", expires_in: Optional[int] = None) -> str:
    exp_seconds = expires_in or settings.JWT_EXPIRATION_SECONDS
    payload = {
        "sub": sub,
        "role": role,
        "exp": datetime.utcnow() + timedelta(seconds=exp_seconds),
        "jti": str(uuid.uuid4()), 
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])


def get_current_token(
      credentials: HTTPAuthorizationCredentials = Depends(_bearer),
      redis=Depends(get_redis),
  ) -> dict:
      if credentials is None:
          raise HTTPException(
              status_code=status.HTTP_401_UNAUTHORIZED,
              detail="Not authenticated",
          )
      try:
          payload = decode_token(credentials.credentials)
          if redis and is_blacklisted(payload.get("jti", ""), redis):
              raise HTTPException(status_code=401, detail="Token revoked")
          return payload
      except jwt.PyJWTError:
          raise HTTPException(
              status_code=status.HTTP_401_UNAUTHORIZED,
              detail="Invalid token",
          )

def get_optional_token(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
) -> Optional[dict]:
    if credentials is None:
        return None
    try:
        return decode_token(credentials.credentials)
    except jwt.PyJWTError:
        return None


def require_admin(payload: dict = Depends(get_current_token)) -> dict:
    if payload.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin only",
        )
    return payload

def create_refresh_token(sub: str) -> str:
    payload = {
        "sub": sub,
        "type": "refresh",
        "jti": str(uuid.uuid4()),
        "exp": datetime.utcnow() + timedelta(seconds=settings.JWT_REFRESH_EXPIRATION_SECONDS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)

def blacklist_token(jti: str, ttl:int, redis) -> None:
    """
    Set the TTL as the redisual time as the token,
    when token expired naturally(setting time), 
    the record in the redis will delete simultaneously and will not consume the memory anymore
    """
    redis.setex(f"blacklist:{jti}", ttl, "1")

def is_blacklisted(jti:str, redis) -> bool:
    """
    Check if current jti token exisrs in redis or not,
    if so, it means the user already logged out and current token is being blacklisted 
    """
    return redis.exists(f"blacklist:{jti}") > 0
    

    
