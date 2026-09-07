"""MongoDB Index Manager — ensures required indexes (TTL, unique) are created and consistent at startup."""
from pymongo import ASCENDING
from pymongo.errors import OperationFailure
from app.config import SETTINGS, logger
from app.db.client import get_db

#Create or recreate a TTL index — drops and retries on any spec conflict.
async def upsert_ttl_index(collection, field: str, name: str, ttl_seconds: int) -> None:
    try:
        await collection.create_index([(field, ASCENDING)], name=name, expireAfterSeconds=ttl_seconds, sparse=True)
    except OperationFailure:
        await collection.drop_index(name)
        await collection.create_index([(field, ASCENDING)], name=name, expireAfterSeconds=ttl_seconds, sparse=True)

#"Create all required indexes — called once at application startup
async def ensure_indexes() -> None:
    db = get_db()
    ttl_seconds = SETTINGS.CHAT_HISTORY_TTL_SECONDS

    await db.user_tokens.create_index("teams_user_id", unique=True)

    await db.chat_sessions.create_index("chat_id", unique=True)
    await db.chat_sessions.create_index([("tenant_id", ASCENDING), ("user_id", ASCENDING)])
    await upsert_ttl_index(db.chat_sessions, "last_active_at", "chat_sessions_ttl", ttl_seconds)

    await upsert_ttl_index(db.checkpoints,      "last_modified_at", "checkpoints_ttl",       ttl_seconds)
    await upsert_ttl_index(db.checkpoint_writes, "last_modified_at", "checkpoint_writes_ttl", ttl_seconds)

    logger.info("MongoDB indexes verified", chat_ttl_seconds=ttl_seconds)
