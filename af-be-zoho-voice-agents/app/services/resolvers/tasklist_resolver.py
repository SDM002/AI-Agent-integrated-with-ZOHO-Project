"""Resolver — match a tasklist (folder) name against a Zoho project's task lists."""
import logging
from typing import Dict

from app.config import SETTINGS
from app.services.zoho.http_client import ZohoHttpClient
from app.utils.string_matching import normalize, score

logger = logging.getLogger(__name__)


async def resolve_tasklist(client: ZohoHttpClient, project_id: str, list_name: str) -> Dict:
    """Resolve tasklist (folder) by name — exact first, then fuzzy with ambiguity detection."""
    try:
        key = normalize(list_name)
        res = await client.get(f"/projects/{project_id}/tasklists/")
        if not res["success"]: return res
        tls = res["value"].get("tasklists", [])

        for tl in tls:
            if normalize(tl.get("name", "")) == key:
                return {"success": True, "value": {"id": tl.get("id_string", str(tl.get("id", ""))), "name": tl["name"]}}

        candidates = []
        for tl in tls:
            sc = score(key, normalize(tl.get("name", "")))
            if sc >= SETTINGS.RESOLVER_STRONG_MATCH:
                candidates.append((sc, tl))
        candidates.sort(key=lambda x: x[0], reverse=True)

        if len(candidates) == 1 or (
            len(candidates) > 1 and candidates[0][0] - candidates[1][0] >= SETTINGS.RESOLVER_AMBIGUITY_GAP
        ):
            tl = candidates[0][1]
            return {"success": True, "value": {"id": tl.get("id_string", str(tl.get("id", ""))), "name": tl["name"]}}

        if len(candidates) >= 2:
            names = [tl.get("name") for _, tl in candidates[:5]]
            return {"success": False, "ambiguous": True,
                    "user_message": f"Multiple folders match '{list_name}': {', '.join(names)}."}

        all_names = [tl.get("name") for tl in tls]
        return {"success": False, "user_message": f"Folder '{list_name}' not found. Available: {', '.join(all_names[:10])}."}
    except Exception as e:
        logger.error("[resolve_tasklist] error: %s", e)
        return {"success": False, "user_message": f"Error finding task list: {e}"}
