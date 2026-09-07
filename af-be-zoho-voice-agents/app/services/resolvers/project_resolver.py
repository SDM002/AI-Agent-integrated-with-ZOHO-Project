"""Resolver — fuzzy-match a project name against Zoho Projects API with pagination and caching."""
import logging
from typing import Dict

from app.config import SETTINGS
from app.services.zoho.http_client import ZohoHttpClient
from app.utils.cache import cache_get, cache_set
from app.utils.string_matching import normalize, score

logger = logging.getLogger(__name__)


async def resolve_project(client: ZohoHttpClient, name: str) -> Dict:
    """Find a project by fuzzy name match. Results are cached by portal + normalized name."""
    ttl = SETTINGS.CACHE_TTL_SECONDS
    key = normalize(name)
    cache_key = (client.portal_id, key)
    cached = await cache_get("project", cache_key, ttl)
    if cached:
        return {"success": True, "value": cached}
    try:
        best, best_score = None, 0
        page, per_page = 1, SETTINGS.RESOLVER_PAGE_SIZE
        while True:
            res = await client.get("/projects/", params={"status": "active", "page": page, "per_page": per_page})
            if not res["success"]: return res
            projects = res["value"].get("projects", [])
            if not projects: break
            for p in projects:
                sc = score(key, normalize(p.get("name", "")))
                if sc > best_score:
                    best_score = sc
                    best = {"id": p.get("id_string", str(p.get("id", ""))), "name": p["name"]}
                if sc == 100:
                    await cache_set("project", cache_key, best, ttl)
                    return {"success": True, "value": best}
            if len(projects) < per_page: break
            page += 1
        if best and best_score >= SETTINGS.RESOLVER_MIN_SCORE:
            await cache_set("project", cache_key, best, ttl)
            return {"success": True, "value": best}
        return {"success": False, "user_message": f"Project '{name}' not found. Try: list active projects"}
    except Exception as e:
        logger.error("[resolve_project] error: %s", e)
        return {"success": False, "user_message": f"Error finding project: {e}"}
