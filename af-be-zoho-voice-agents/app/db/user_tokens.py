"""User token storage — OAuth token CRUD with encryption at rest."""
from datetime import datetime, timezone
from typing import Optional
from app.config import SETTINGS, logger
from app.db.client import get_db
from app.utils.crypto import encrypt, decrypt

# --- Internal Helpers--
def col():      return get_db().user_tokens
def now():      return datetime.now(timezone.utc)
def key(uid):   return {"teams_user_id": uid.lower()}

# --- Token Retrieval--
async def get_user_token(teams_user_id: str) -> Optional[dict]:
    """Fetch and decrypt a user's OAuth token record. Returns None if not found."""
    try:
        record = await col().find_one(key(teams_user_id))
        if not record:
            return None
        record = dict(record)
        record["access_token"]  = decrypt(record.get("access_token", ""))
        record["refresh_token"] = decrypt(record.get("refresh_token", ""))
        return record
    except Exception as e:
        logger.error("get_user_token failed", user=teams_user_id, error=str(e))
        return None

# --- Token Persistence--
async def save_user_token(
    teams_user_id: str,
    teams_tenant_id: str,
    teams_oid: str,
    zoho_user_id: str,
    zoho_org_id: str,
    email: str,
    access_token: str,
    refresh_token: str,
    expires_at: float,
    api_domain: str = "",
    portals: list = None,
    portal_selection_pending: bool = False,
) -> None:
    """Upsert a user's Zoho OAuth token — encrypts tokens before persisting."""
    ts = now()
    await col().update_one(key(teams_user_id), {
        "$set": {
            "teams_user_id":            teams_user_id.lower(),
            "teams_tenant_id":          teams_tenant_id,
            "teams_oid":                teams_oid,
            "zoho_user_id":             zoho_user_id,
            "zoho_org_id":              zoho_org_id,
            "email":                    email,
            "access_token":             encrypt(access_token),
            "refresh_token":            encrypt(refresh_token),
            "expires_at":               expires_at,
            "api_domain":               api_domain or SETTINGS.ZOHO_API_DOMAIN,
            "portals":                  portals or [],
            "portal_selection_pending": portal_selection_pending,
            "updated_at":               ts,
        },
        "$setOnInsert": {"created_at": ts},
    }, upsert=True)
    logger.info("Token saved", user=email)


async def update_access_token(teams_user_id: str, access_token: str, expires_at: float) -> None:
    """Update only the access token after refresh — leaves refresh_token intact."""
    await col().update_one(key(teams_user_id), {"$set": {
        "access_token": encrypt(access_token),
        "expires_at":   expires_at,
        "updated_at":   now(),
    }})

# --- User State Updates--
async def finalize_portal_selection(
    teams_user_id: str, portal_id: str, portal_name: str = "", api_domain: str = ""
) -> None:
    """Persist the user's chosen Zoho portal — clears selection_pending flag."""
    update = {
        "zoho_org_id":              portal_id,
        "portal_name":              portal_name,
        "portal_selection_pending": False,
        "portals":                  [],
        "updated_at":               now(),
    }
    if api_domain:
        update["api_domain"] = api_domain
    await col().update_one(key(teams_user_id), {"$set": update})
    logger.info("Portal finalized", user=teams_user_id, portal=portal_id)


async def update_email(teams_user_id: str, email: str) -> None:
    """Backfill email when it wasn't captured during OAuth."""
    await col().update_one(key(teams_user_id), {"$set": {"email": email, "updated_at": now()}})

# --- Cleanup---
async def delete_user_token(teams_user_id: str) -> None:
    """Remove a user's OAuth token from DB (logout / disconnect)."""
    await col().delete_one(key(teams_user_id))
    logger.info("Token deleted", user=teams_user_id)
