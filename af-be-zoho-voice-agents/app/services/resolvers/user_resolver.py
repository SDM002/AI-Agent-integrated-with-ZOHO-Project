"""Resolvers — match users by name (string) or email (exact, cached) against Zoho portal users."""
import logging
from typing import Dict, List

from app.config import SETTINGS
from app.services.zoho.http_client import ZohoHttpClient
from app.utils.cache import cache_get, cache_set
from app.utils.string_matching import score

logger = logging.getLogger(__name__)


async def resolve_user_by_name(client: ZohoHttpClient, name: str, project_id: str = "") -> Dict:
    """String-match user by display name, full name, or email local part across project + portal users."""
    try:
        target = name.strip().lower()
        users: List[Dict] = []
        seen: set = set()

        if project_id:
            r = await client.get(f"/projects/{project_id}/users/")
            if r["success"]:
                for u in r["value"].get("users", []):
                    e = (u.get("email") or "").lower()
                    if e and e not in seen:
                        seen.add(e); users.append(u)

        r2 = await client.get("/users/")
        if r2["success"]:
            for u in r2["value"].get("users", []):
                e = (u.get("email") or "").lower()
                if e and e not in seen:
                    seen.add(e); users.append(u)

        scored = []
        for u in users:
            tokens = set()
            for field in ["display_name", "full_name", "name", "first_name", "last_name"]:
                val = (u.get(field) or "").strip().lower()
                if val:
                    tokens.add(val)
                    tokens.update(w for w in val.split() if len(w) > 1)
            e_local = (u.get("email") or "").split("@")[0].lower()
            if e_local: tokens.add(e_local)

            best_sc = max((score(target, t) for t in tokens), default=0)
            if best_sc >= SETTINGS.RESOLVER_STRONG_MATCH:
                uid = str(u.get("zpuid") or u.get("id") or u.get("zuid", ""))
                display = (u.get("display_name") or u.get("name") or u.get("full_name") or u.get("email", ""))
                scored.append({"score": best_sc, "zpuid": uid, "name": display, "email": u.get("email", "")})

        scored.sort(key=lambda x: x["score"], reverse=True)
        if not scored:
            return {"success": False, "user_message": f"No user found matching '{name}'."}

        top = scored[0]
        if (
            len(scored) == 1
            or top["score"] == 100
            or (len(scored) > 1 and top["score"] - scored[1]["score"] >= SETTINGS.RESOLVER_AMBIGUITY_GAP)
        ):
            return {"success": True, "value": top}

        candidates = [{"name": s["name"], "email": s["email"], "zpuid": s["zpuid"]} for s in scored[:5]]
        return {
            "success": False, "ambiguous": True, "candidates": candidates,
            "user_message": f"Multiple people match '{name}': "
                            + ", ".join(f"{c['name']} ({c['email']})" for c in candidates),
        }
    except Exception as e:
        logger.error("[resolve_user_by_name] error: %s", e)
        return {"success": False, "user_message": f"Error finding user: {e}"}


async def resolve_user_by_email(client: ZohoHttpClient, email: str, project_id: str = "") -> Dict:
    """Resolve user zpuid from email by listing portal users via v1 API (result cached by TTL)."""
    try:
        from email_validator import validate_email, EmailNotValidError
        validate_email(email, check_deliverability=False)
    except Exception:
        return {"success": False, "user_message": f"'{email}' is not a valid email address."}

    ttl = SETTINGS.CACHE_TTL_SECONDS
    target = email.strip().lower()
    cache_key = (client.portal_id, target)
    cached = await cache_get("user", cache_key, ttl)
    if cached:
        return {"success": True, "value": cached}
    try:
        users = []
        res = await client.get("/users/")
        if res["success"]:
            users = res["value"].get("users", [])
        elif project_id:
            # Fallback to project users if portal users is unauthorized (401)
            p_res = await client.get(f"/projects/{project_id}/users/")
            if p_res["success"]:
                users = p_res["value"].get("users", [])
            else:
                return p_res
        else:
            # Fallback for non-admin users who get a 401 when fetching portal-wide users list.
            # still succeed because the email is valid and can be used directly by caller tools.
            return {
                "success": True,
                "value": {
                    "zpuid": "",
                    "name": target,
                    "email": target
                }
            }
            
        target_local = target.split("@")[0]
        from app.utils.string_matching import normalize
        target_name_guess = normalize(target_local)
        
        for u in users:
            user_email = (u.get("email") or "").lower()
            user_name_norm = normalize(u.get("name", ""))
            
            # Match by email exact, email local part, OR name (if Zoho hid the email)
            if (user_email == target or 
                (user_email and user_email.split("@")[0] == target_local) or 
                (user_name_norm and user_name_norm == target_name_guess)):
                
                result = {
                    "zpuid": str(u.get("zpuid") or u.get("id", "")),
                    "name":  u.get("name", ""),
                    "email": u.get("email", email),
                }
                await cache_set("user", cache_key, result, ttl)
                if user_email:
                    await cache_set("user", (client.portal_id, user_email), result, ttl)
                return {"success": True, "value": result}
    
        available = [u.get("email", "") for u in users]
        logger.warning("[resolve_user_by_email] '%s' not found. Available: %s", email, available)
        return {"success": False, "user_message": f"User '{email}' not found."}
    except Exception as e:
        logger.error("[resolve_user_by_email] error: %s", e)
        return {"success": False, "user_message": f"Error finding user: {e}"}
