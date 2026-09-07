"""Redis async client — single shared connection pool for cache and rate-limit operations."""
import redis.asyncio as aioredis
from app.config import SETTINGS

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.Redis(
            host=SETTINGS.REDIS_URL,
            port=SETTINGS.REDIS_PORT,
            username=SETTINGS.REDIS_USERNAME,
            password=SETTINGS.REDIS_KEY,
            decode_responses=True
        )
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None
