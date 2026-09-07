"""Chat Session Store — manages mapping between chat_id, user_id, and tenant_id with activity tracking."""

from datetime import datetime, timezone
from typing import Optional
from app.config import logger
from app.db.client import get_db


def col():  return get_db().chat_sessions  # DB Collection Helper
def now():  return datetime.now(timezone.utc)  # Current UTC Timestamp Helper

# Save or Update Chat Session
async def save_chat_session(chat_id: str, tenant_id: str, user_id: str) -> None:
    """Upsert a chat session record — refreshes last_active_at on every message."""
    if not chat_id:
        return
    ts = now()
    await col().update_one(
        {"chat_id": chat_id},
        {
            "$set": {
                "chat_id":        chat_id,
                "tenant_id":      tenant_id,
                "user_id":        user_id.lower(),
                "last_active_at": ts,
            },
            "$setOnInsert": {"created_at": ts},
        },
        upsert=True,
    )

 # Get Chat Session by ID
async def get_chat_session(chat_id: str) -> Optional[dict]:
    """Return the session record for a given Teams chat_id, or None if not found."""
    if not chat_id:
        return None
    record = await col().find_one({"chat_id": chat_id})
    return dict(record) if record else None

# Get All Sessions for User
async def get_user_sessions(user_id: str) -> list[dict]:
    """Return all chat sessions belonging to a user — used for full cleanup on logout."""
    cursor = col().find({"user_id": user_id.lower()}, {"chat_id": 1, "tenant_id": 1})
    return [{"chat_id": r["chat_id"], "tenant_id": r["tenant_id"]} async for r in cursor]

# Delete Single Session by Chat ID
async def delete_chat_session(chat_id: str) -> None:
    """Delete one chat_session record by chat_id (called on new chat)."""
    await col().delete_one({"chat_id": chat_id})

# Delete All Sessions for User
async def delete_user_sessions(user_id: str) -> None:
    """Delete all chat_session records for a user (metadata only — not checkpoints)."""
    result = await col().delete_many({"user_id": user_id.lower()})
    logger.info("Chat sessions deleted", user=user_id, count=result.deleted_count)
