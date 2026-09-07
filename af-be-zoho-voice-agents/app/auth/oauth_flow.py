"""
Zoho OAuth login flow — builds the Zoho consent URL, verifies the signed state on callback
and exchanges the authorisation code for access and refresh tokens.
"""
import asyncio
import base64
import hashlib
import hmac as hmac_lib
import json
import random
import time
import urllib.parse
import httpx

from app.config import SETTINGS, logger
from app.config.settings import ZOHO_SCOPES
from app.services.http_client import get_http

state_key: str | None = None  # Cached key for signing OAuth state

# Generate and return state signing key (derived from ENCRYPTION_KEY)
def get_state_key() -> str:
    global state_key
    if state_key is None:
        state_key = hashlib.sha256(
            f"zoho-state:{SETTINGS.ENCRYPTION_KEY}".encode()
        ).hexdigest()
    return state_key

# Retry helper (Send POST request → retry on temporary failures → stop on real errors → return response)
async def post_token(url: str, params: dict) -> httpx.Response:
    last_exc = None
    max_retries = SETTINGS.OAUTH_MAX_RETRIES
    for attempt in range(max_retries):
        try:
            r = await get_http().post(url, params=params)
            if r.status_code == 429 and attempt < max_retries - 1:
                await asyncio.sleep((2 ** attempt) + random.uniform(0, 0.5))
                continue
            return r
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            last_exc = e
            if attempt < max_retries - 1:
                await asyncio.sleep((2 ** attempt) + random.uniform(0, 0.5))
    raise last_exc or httpx.RequestError("Max retries exceeded")

# Build login URL — takes user + tenant → builds secure login URL → user goes to Zoho → comes back with verified identity
def build_auth_url(teams_user_id: str, teams_tenant_id: str) -> str:
    payload = {
        "teams_user_id":   teams_user_id,
        "teams_tenant_id": teams_tenant_id,
        "iat":             int(time.time()),
    }
    raw = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    sig = hmac_lib.new(get_state_key().encode(), raw.encode(), hashlib.sha256).hexdigest()
    params = {
        "scope":         ",".join(ZOHO_SCOPES),
        "client_id":     SETTINGS.ZOHO_CLIENT_ID,
        "response_type": "code",
        "access_type":   "offline",
        "redirect_uri":  SETTINGS.ZOHO_REDIRECT_URI,
        "state":         f"{raw}.{sig}",
        "prompt":        "consent",
    }
    query = "&".join(f"{k}={urllib.parse.quote(str(v), safe=',')}" for k, v in params.items())
    return f"{SETTINGS.ZOHO_AUTH_URL}?{query}"

# Decode and validate OAuth state (verify hash(data + secret_key) and expiry)
def decode_state(state: str) -> dict:
    try:
        raw, sig = state.rsplit(".", 1)
        expected = hmac_lib.new(get_state_key().encode(), raw.encode(), hashlib.sha256).hexdigest()
        if not hmac_lib.compare_digest(sig, expected):
            raise ValueError("Invalid state signature")
        payload = json.loads(base64.urlsafe_b64decode(raw.encode()).decode())
        if time.time() - payload.get("iat", 0) > SETTINGS.OAUTH_STATE_MAX_AGE:
            raise ValueError("State expired")
        return payload
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"State decode failed: {type(e).__name__}")

# OAuth Token Exchange — Authorization Code → Access & Refresh Tokens
async def exchange_code(code: str) -> dict:
    r = await post_token(SETTINGS.ZOHO_TOKEN_URL, params={
        "grant_type":    "authorization_code",
        "client_id":     SETTINGS.ZOHO_CLIENT_ID,
        "client_secret": SETTINGS.ZOHO_CLIENT_SECRET,
        "redirect_uri":  SETTINGS.ZOHO_REDIRECT_URI,
        "code":          code,
    })
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        logger.error("Code exchange failed", error=data["error"])
        raise ValueError(f"Zoho token error: {data['error']}")
    return data