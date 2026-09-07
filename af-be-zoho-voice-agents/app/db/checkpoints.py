"""Checkpoint TTL Manager — refreshes expiry timestamps for agent state to keep active sessions alive."""
from datetime import datetime, timezone

# Current UTC Timestamp Helpe
def now(): return datetime.now(timezone.utc)

#  Refresh Checkpoint TTL
async def touch_checkpoint_ttl(db, thread_id: str) -> None:
    """Reset last_modified_at on checkpoint docs so TTL clock restarts on every message."""
    ts = now()
    await db.checkpoints.update_many(
        {"thread_id": thread_id}, {"$set": {"last_modified_at": ts}}
    )
    await db.checkpoint_writes.update_many(
        {"thread_id": thread_id}, {"$set": {"last_modified_at": ts}}
    )
