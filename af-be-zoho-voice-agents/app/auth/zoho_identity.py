"""
Zoho Identity & Portal Service — retrieves authenticated user details
and available project portals after OAuth.
"""
from app.config import SETTINGS, logger
from app.config.settings import ZOHO_PROJECTS_DOMAIN_MAP
from app.services.http_client import get_http

# Zoho Projects API Domain Resolver (Region-based mapping with fallback)
def projects_domain(api_domain: str) -> str:
    for domain_key, val in ZOHO_PROJECTS_DOMAIN_MAP.items():
        if domain_key in api_domain:
            return val
    return SETTINGS.ZOHO_PROJECTS_API_DOMAIN  # fallback to .env configured default

# Fetch Zoho User Profile & Available Portals (Identity + Org Discovery)
# Main flow: User info → normalize → fetch portals → normalize portals
async def get_zoho_user_info(access_token: str, api_domain: str) -> dict:
    headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
    c = get_http()
    
    user_resp = await c.get(SETTINGS.ZOHO_USERINFO_URL, headers=headers) # Step 1: Fetch User Profile
    user_resp.raise_for_status()
    info = user_resp.json()

    # Step 2: Normalize User Fields (Handle Zoho inconsistencies)
    email        = info.get("Email") or info.get("email") or info.get("EmailId") or ""
    zoho_user_id = str(info.get("ZUID") or info.get("Zuid") or "")

    domain = projects_domain(api_domain)   # Step 3: Resolve Correct Projects Domain
    portal_resp = await c.get(f"https://{domain}/restapi/portals/", headers=headers) # Step 4: Fetch Available Portals
    try:
        portal_resp.raise_for_status()  
    except Exception:
        # Handle API Errors (Auth / Permission Issues)
        logger.error(
            "Zoho portals fetch failed",
            status=portal_resp.status_code,
            domain=domain,
            body=portal_resp.text[:500],
        )
        raise
    
    # Step 5: Normalize Portal Data
    raw_portals = portal_resp.json().get("portals", []) or []
    portals = []
    for p in raw_portals:
        # Prefer numeric id for v3 API compatibility; id_string is often the slug (login_id)
        pid_numeric = str(p.get("id") or "").strip()
        pid_slug    = str(p.get("id_string") or "").strip()
        # Use numeric if it looks like a number; otherwise fall back to id_string
        pid = pid_numeric if pid_numeric.isdigit() else (pid_slug or pid_numeric)
        if not pid:
            continue
        portals.append({"id": pid, "slug": pid_slug, "name": p.get("name", "")})
    return {"zoho_user_id": zoho_user_id, "email": email, "portals": portals}