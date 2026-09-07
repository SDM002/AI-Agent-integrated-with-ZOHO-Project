"""Session manager — clear per-chat or all-user agent thread checkpoints."""
import app.services.checkpoint as _cp

from app.config import logger
from app.db.chat_sessions import get_user_sessions, delete_user_sessions, delete_chat_session


async def clear_session(chat_id: str, tenant_id: str) -> None:
    """Delete checkpoints + chat_session record for one chat thread (called on New Chat)."""
    thread_id = f"{tenant_id}:{chat_id}"
    if _cp.checkpointer:
        await _cp.checkpointer.adelete_thread(thread_id)
    await delete_chat_session(chat_id)
    logger.info("Session cleared", tenant=tenant_id, chat=chat_id)


async def clear_all_user_sessions(user_id: str) -> None:
    """Delete ALL checkpoint threads + chat_session records for a user (called on logout)."""
    sessions = await get_user_sessions(user_id)
    for s in sessions:
        thread_id = f"{s['tenant_id']}:{s['chat_id']}"
        if _cp.checkpointer:
            try:
                await _cp.checkpointer.adelete_thread(thread_id)
            except Exception:
                pass
    await delete_user_sessions(user_id)
    logger.info("All sessions cleared on logout", user=user_id, count=len(sessions))
