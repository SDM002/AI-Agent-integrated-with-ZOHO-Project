"""Zoho client factory — builds a configured ZohoHttpClient for the current user."""
from app.services.zoho.http_client import ZohoHttpClient


async def build_zoho_client(user_id: str, api_domain: str = None, portal_id: str = None) -> ZohoHttpClient:
    """Create a ZohoHttpClient for the given user by resolving a valid Zoho access token."""
    from app.auth.token_manager import get_valid_token
    from app.db.user_tokens import get_user_token

    access_token = await get_valid_token(user_id)
    if not access_token:
        raise RuntimeError(f"No Zoho access token available for user_id={user_id}. Complete OAuth first.")

    record = await get_user_token(user_id)
    if record:
        api_domain        = api_domain or record.get("api_domain") or ""
        portal_numeric_id = record.get("zoho_org_id") or ""
        portal_slug       = portal_id or record.get("zoho_org_id") or ""
    else:
        portal_numeric_id = ""
        portal_slug       = portal_id or ""

    return ZohoHttpClient(
        access_token=access_token,
        api_domain=api_domain,
        portal_id=portal_slug,
        portal_numeric_id=portal_numeric_id,
        tenant_id=user_id,
    )
