"""Resolver — string-match a task name against tasks in a Zoho project with pagination."""
import logging
from typing import Dict

from app.config import SETTINGS
from app.services.zoho.http_client import ZohoHttpClient
from app.utils.string_matching import score

logger = logging.getLogger(__name__)


async def resolve_task(client: ZohoHttpClient, project_id: str, task_name: str, min_score: int = None) -> Dict:
    """
    String-match task name to an existing task.
    Args:
        min_score: Minimum score to consider a match.
                   Defaults to SETTINGS.RESOLVER_MIN_SCORE (50).
                   Pass 90 for duplicate detection to avoid false positives.
    """
    if min_score is None:
        min_score = SETTINGS.RESOLVER_MIN_SCORE
    try:
        key = task_name.lower()
        best, best_score = None, 0
        page, per_page = 1, SETTINGS.RESOLVER_PAGE_SIZE
        while True:
            res = await client.get(f"/projects/{project_id}/tasks/",
                                   params={"page": page, "per_page": per_page,
                                           "sort_by": "DESC(last_modified_time)"})
            if not res["success"]: return res
            tasks = res["value"].get("tasks", [])
            if not tasks: break
            for t in tasks:
                # Exact match on Zoho display/prefix ID (e.g. "TN1-T1")
                prefix_id = t.get("task_prefix_id") or t.get("id_string") or ""
                if key == str(prefix_id).lower():
                    return {"success": True, "value": {"id": t.get("id_string", str(t.get("id", ""))), "name": t["name"]}}
                sc = score(key, t.get("name", "").lower())
                if sc > best_score:
                    best_score = sc
                    best = {"id": t.get("id_string", str(t.get("id", ""))), "name": t["name"]}
                if sc == 100: return {"success": True, "value": best}
            if len(tasks) < per_page: break
            page += 1
        if best and best_score >= min_score: return {"success": True, "value": best}
        return {"success": False, "user_message": f"Task '{task_name}' not found."}
    except Exception as e:
        logger.error("[resolve_task] error: %s", e)
        return {"success": False, "user_message": f"Error finding task: {e}"}
