"""Redis-backed TTL cache — generic helpers plus Zoho-specific slot accessors.
Replaces the previous in-memory Python dicts with Redis so all backend pods
share the same cache and rate-limit state (multi-pod safe).
"""
import json
from typing import Optional

from app.config import SETTINGS
from app.db.redis import get_redis


async def cache_get(namespace: str, key: tuple, ttl: int) -> Optional[dict]:
    r = await get_redis()
    raw = await r.get(f"cache:{namespace}:{key}")
    return json.loads(raw) if raw else None


async def cache_set(namespace: str, key: tuple, value, ttl: int) -> None:
    r = await get_redis()
    await r.setex(f"cache:{namespace}:{key}", ttl, json.dumps(value))


# Return slots recently created by the agent but not yet reflected in Zoho (eventual consistency bridge)
async def get_slots(email: str, date: str) -> list:
    r = await get_redis()
    raw = await r.get(f"slot:{email.lower().strip()}:{date}")
    return json.loads(raw) if raw else []


# Store a newly created slot to bridge Zoho's sync delay — survives pod restarts
async def set_slot(email: str, date: str, start_mins: int, end_mins: int, task: str) -> None:
    r = await get_redis()
    key = f"slot:{email.lower().strip()}:{date}"
    raw = await r.get(key)
    slots = json.loads(raw) if raw else []
    slots.append({"start_mins": start_mins, "end_mins": end_mins, "task": task})
    await r.setex(key, SETTINGS.CACHE_TTL_SECONDS, json.dumps(slots))
