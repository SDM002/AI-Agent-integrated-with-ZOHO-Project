"""
Zoho OAuth routes — Handles authentication, token lifecycle, portal selection, and session reset.
"""
import time
import urllib.parse
from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import RedirectResponse
from app.config import SETTINGS, logger
from app.services.session_manager import clear_session, clear_all_user_sessions
from app.db.user_tokens import (
    get_user_token, save_user_token,
    delete_user_token, finalize_portal_selection, update_access_token,
)
from app.auth.oauth_flow import build_auth_url, decode_state, exchange_code  # OAuth login + callback flow
from app.auth.zoho_identity import get_zoho_user_info                         # User profile + portal discovery
from app.auth.token_manager import refresh_access_token, invalidate_token_cache  # Token lifecycle

router = APIRouter(prefix="/auth", tags=["auth"]) #Auth Endpoint Routing Setup

#START OAUTH FLOW
@router.get("/zoho/login")      # Redirect user to Zoho consent page 
async def zoho_login(teams_user_id: str, teams_tenant_id: str = "default"):
    url = build_auth_url(teams_user_id, teams_tenant_id)
    logger.info("OAuth login", user=teams_user_id, tenant=teams_tenant_id)
    return RedirectResponse(url)

#OAUTH CALLBACK HANDLER
@router.get("/zoho/callback")  # Zoho redirects here after user approves — exchange code for tokens
async def zoho_callback(code: str, state: str):      
    try: # Validate state
        state_data      = decode_state(state)
        teams_user_id   = state_data["teams_user_id"]
        teams_tenant_id = state_data["teams_tenant_id"]
    except ValueError as e:
        logger.warning("OAuth callback: bad state", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid or expired authorization request")
    try:      # Exchange code for tokens
        data = await exchange_code(code)
    except Exception as e:
        logger.error("Code exchange failed", error=type(e).__name__)
        return RedirectResponse(f"{SETTINGS.APP_URL}?connected=false")

    expires_at = time.time() + data.get("expires_in", SETTINGS.ZOHO_TOKEN_DEFAULT_EXPIRY) - SETTINGS.TOKEN_EXPIRY_BUFFER
    api_domain = data.get("api_domain") or SETTINGS.ZOHO_API_DOMAIN
   
    try:  # Fetch Zoho user profile (orgs, email)
        user_info = await get_zoho_user_info(data["access_token"], api_domain)
    except Exception as e:
        logger.warning("User info fetch failed", error=type(e).__name__)
        user_info = {"zoho_user_id": "", "email": "", "portals": []}

    portals  = user_info["portals"]
    pending  = len(portals) >= 1   #user confirm their org on the next screen
    org_id   = ""
    # Save token + user mapping
    # Fallback: if Zoho didn't return an email, use teams_user_id (which is the email in web context)
    stored_email = user_info["email"] or (teams_user_id if "@" in teams_user_id else "")
    await save_user_token(
        teams_user_id   = teams_user_id,
        teams_tenant_id = teams_tenant_id,
        teams_oid       = user_info.get("teams_oid", ""),   # Entra Object ID — stable identifier
        zoho_user_id    = user_info["zoho_user_id"],
        zoho_org_id     = org_id,
        email           = stored_email,
        access_token    = data["access_token"],
        refresh_token   = data.get("refresh_token", ""),
        expires_at      = expires_at,
        api_domain      = api_domain,
        portals         = portals,
        portal_selection_pending = pending,
    )
    # Redirect based on portal requirement
    if pending:
        return RedirectResponse(
            f"{SETTINGS.APP_URL}/select-portal"
            f"?user_id={urllib.parse.quote(teams_user_id)}"
            f"&email={urllib.parse.quote(user_info['email'])}"
        )
    logger.info("OAuth complete", user=teams_user_id, email=user_info["email"]) # If NO portal selection needed ,Redirect to main app (connected)
    return RedirectResponse(f"{SETTINGS.APP_URL}?connected=true&email={user_info['email']}")

#CONNECTION STATUS
@router.get("/zoho/status")
async def zoho_status(teams_user_id: str):
    record = await get_user_token(teams_user_id)  # Returns connection state — auto-refreshes token if expired
    if not record:
        return {"connected": False}
    # Refresh token if expired
    if record["expires_at"] < time.time(): 
        try:
            new_token, new_expires = await refresh_access_token(record["refresh_token"])
            await update_access_token(teams_user_id, new_token, new_expires)
        except Exception:
            return {"connected": False}

    if record.get("portal_selection_pending"):
        return {"connected": False, "pending_portal": True, "email": record.get("email", "")}

    return {
        "connected": True,
        "email":     record.get("email", ""),
        "org_id":    record.get("zoho_org_id", ""),
    }

#GET PORTALS
@router.get("/zoho/portals")
async def get_portals(teams_user_id: str):
    record = await get_user_token(teams_user_id) # Returns the list of Zoho orgs for the portal picker UI
    if not record:
        raise HTTPException(status_code=404, detail="User not found. Complete OAuth first.")
    return {
        "portals": record.get("portals", []),
        "email":   record.get("email", ""),
        "pending": record.get("portal_selection_pending", False),
    }

#PORTAL SELECTION
@router.post("/zoho/select-portal")
async def select_portal(payload: dict = Body(...)):
    teams_user_id = payload.get("teams_user_id", "").strip()  # Finalizes portal selection after user picks their Zoho org
    portal_id     = payload.get("portal_id",     "").strip()
    portal_name   = payload.get("portal_name",   "").strip()

    if not teams_user_id or not portal_id:
        raise HTTPException(status_code=400, detail="teams_user_id and portal_id are required")

    record = await get_user_token(teams_user_id)
    if not record:
        raise HTTPException(status_code=404, detail="User not found. Complete OAuth first.")

    # Accept both numeric id and slug from portals list
    allowed = set()
    for p in record.get("portals", []):
        allowed.add(p.get("id", ""))
        allowed.add(p.get("slug", ""))
    allowed.discard("")
    if allowed and portal_id not in allowed:
        raise HTTPException(status_code=400, detail="Invalid portal_id")

    await finalize_portal_selection(
        teams_user_id = teams_user_id,
        portal_id     = portal_id,
        portal_name   = portal_name,
        api_domain    = record.get("api_domain", ""),
    )
    logger.info("Portal selected", user=teams_user_id, portal=portal_id)
    return {"connected": True, "email": record.get("email", ""), "portal_id": portal_id}

#DISCONNECT USER — clears all caches, checkpoints, chat sessions, and OAuth tokens
@router.delete("/zoho/disconnect")
async def zoho_disconnect(teams_user_id: str):
    invalidate_token_cache(teams_user_id)           # evict cached access token immediately
    await clear_all_user_sessions(teams_user_id)    # delete checkpoints + chat_sessions
    await delete_user_token(teams_user_id)          # delete OAuth tokens from MongoDB
    logger.info("User disconnected", user=teams_user_id)
    return {"message": "Disconnected"}

#NEW CHAT RESET — clears history for a specific Teams chat session
@router.post("/zoho/new-chat")
async def zoho_new_chat(chat_id: str, tenant_id: str):
    await clear_session(chat_id=chat_id, tenant_id=tenant_id)
    logger.info("New chat started", chat=chat_id, tenant=tenant_id)
    return {"message": "Ready for new chat"}