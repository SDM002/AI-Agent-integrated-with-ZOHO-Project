"""
Zoho Token Manager — handles access token caching, refresh, and concurrency control
"""
import asyncio
import time

from app.config import SETTINGS, logger
from app.db.user_tokens import get_user_token, update_access_token
from app.auth.oauth_flow import post_token

# --- Token Refresh Error-(Raised when Zoho token refresh fails and re-authentication is required.)
class TokenRefreshError(Exception):
    pass

# -- In-Memory Token Cache --
token_cache: dict[str, tuple[str, float]] = {}  

# Remove cached access token for user (called on logout or disconnect)
def invalidate_token_cache(user_id: str) -> None:
    """Remove a user's cached token — call this on logout or disconnect."""
    token_cache.pop(user_id.lower(), None)

#--- Refresh Lock Management ----
refresh_locks: dict = {}  # Per-user async locks to prevent concurrent token refresh races
locks_guard: asyncio.Lock | None = None  # Global lock to safely manage creation of per-user locks

#--Global Lock Initializer--
def get_guard() -> asyncio.Lock:
    global locks_guard
    if locks_guard is None:
        locks_guard = asyncio.Lock()
    return locks_guard

# --- Per-User Refresh Lock---
async def get_refresh_lock(user_id: str) -> asyncio.Lock:
    async with get_guard():
        if user_id not in refresh_locks:
            refresh_locks[user_id] = asyncio.Lock()
        return refresh_locks[user_id]

# Exchange refresh token for a new access token
async def refresh_access_token(refresh_token: str) -> tuple[str, float]:
    r = await post_token(SETTINGS.ZOHO_TOKEN_URL, params={
        "grant_type":    "refresh_token",
        "client_id":     SETTINGS.ZOHO_CLIENT_ID,
        "client_secret": SETTINGS.ZOHO_CLIENT_SECRET,
        "refresh_token": refresh_token,
    })
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        logger.error("Token refresh failed", error=data["error"])
        raise TokenRefreshError(f"Zoho rejected refresh: {data['error']}")
    return data["access_token"], time.time() + data.get("expires_in", SETTINGS.ZOHO_TOKEN_DEFAULT_EXPIRY) - SETTINGS.TOKEN_EXPIRY_BUFFER

# -- Get Valid Access Token (Cache → DB → Refresh) ---
async def get_valid_token(teams_user_id: str) -> str | None:
    uid = teams_user_id.lower()
    threshold = SETTINGS.TOKEN_REFRESH_THRESHOLD

    # -- Step 1: Check in-memory cache --
    cached_token, cached_expiry = token_cache.get(uid, (None, 0))
    if cached_token and cached_expiry > time.time() + threshold:
        return cached_token

    # -- Step 2: Fetch from database--
    record = await get_user_token(uid)
    if not record:
        return None

    # ── Step 3: Token still fresh in DB — warm the cache and return ──
    if record["expires_at"] > time.time() + threshold:
        token_cache[uid] = (record["access_token"], record["expires_at"])
        return record["access_token"]

    # Step 4 & 5: Handle Expired Token (Lock → Double-Check → Refresh) --
    lock = await get_refresh_lock(uid)
    async with lock:
         # Double-check: token may have been refreshed while waiting for the lock
        record = await get_user_token(uid) 
        if not record:
            return None
        if record["expires_at"] > time.time() + threshold:
            token_cache[uid] = (record["access_token"], record["expires_at"])
            return record["access_token"]

        # Still expired — call Zoho, save to DB, update cache
        new_token, new_expires = await refresh_access_token(record["refresh_token"])
        await update_access_token(uid, new_token, new_expires)
        token_cache[uid] = (new_token, new_expires)
        logger.info("Token refreshed", user=uid)
        return new_token