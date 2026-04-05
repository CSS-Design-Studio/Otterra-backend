from typing import Optional
from redis import Redis
from app.core.config import settings

# 全域 Redis 客戶端
_redis_client: Optional[Redis] = None

def get_redis() -> Optional[Redis]:
    """
    取得 Redis 客戶端
    如果 Redis 未啟用，返回 None
    """
    global _redis_client

    if not settings.REDIS_ENABLED:
        return None

    if _redis_client is None:
        _redis_client = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
            db=settings.REDIS_DB,
            decode_responses=True  # 自動解碼為字串
        )

    return _redis_client

def close_redis():
    """關閉 Redis 連接"""
    global _redis_client
    if _redis_client:
        _redis_client.close()
        _redis_client = None
