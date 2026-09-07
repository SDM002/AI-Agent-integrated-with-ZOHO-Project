"""Resolvers — find a Zoho issue/bug by string title match using the v3 API."""
import logging
from typing import Tuple, Optional

from app.services.zoho.http_client import ZohoHttpClient
from app.utils.string_matching import normalize, score

logger = logging.getLogger(__name__)


async def resolve_issue(
    client: ZohoHttpClient,
    proj_id: str,
    title: str,
    min_score: int = 80,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Find an issue ID by fuzzy-matching its name via the v3 issues list.
    Returns (issue_id, found_name, error_message).
    error_message is None on success; issue_id/found_name are None on failure.
    """
    try:
        res = await client.get_v3(f"/projects/{proj_id}/issues", params={"per_page": 100, "page": 1})
        if not res["success"]:
            return None, None, res["user_message"]

        issues = (
            res["value"].get("issues")
            or res["value"].get("bugs")
            or []
        )

        target = normalize(title)
        best, best_sc = None, 0
        for iss in issues:
            name = iss.get("name") or iss.get("title") or ""
            s = score(target, normalize(name))
            if s > best_sc:
                best_sc, best = s, iss

        if not best or best_sc < min_score:
            return None, None, f"Issue '{title}' not found in this project."

        issue_id   = str(best.get("id", ""))
        found_name = best.get("name") or best.get("title") or title
        return issue_id, found_name, None

    except Exception as e:
        logger.error("[resolve_issue] error: %s", e)
        return None, None, f"Error finding issue: {e}"


async def get_field_options(client: ZohoHttpClient, proj_id: str, field: str) -> list:
    """
    Fetch field options (id + name) from the v1 defaultfields endpoint.
    Used to resolve severity/status names to Zoho IDs for v3 payloads.
    field: 'severity' | 'status' | 'classification' | 'reproducible'
    """
    try:
        res = await client.get(f"/projects/{proj_id}/bugs/defaultfields/")
        if not res["success"]:
            return []
        raw = res["value"]
        df  = raw.get("defaultfields", raw)
        if not isinstance(df, dict):
            return []

        # Keys use "{field}_details" pattern (e.g. "severity_details", "status_details")
        # Items use "{field}_id" / "{field}_name" (e.g. "severity_id", "severity_name")
        items = df.get(f"{field}_details") or df.get(field) or []
        id_key   = f"{field}_id"
        name_key = f"{field}_name"
        result = []
        for item in items:
            oid  = item.get(id_key) or item.get("id", "")
            name = item.get(name_key) or item.get("name") or item.get("type", "")
            if oid and name:
                result.append({"id": str(oid), "name": name})
        return result
    except Exception:
        return []


async def resolve_field_id(
    client: ZohoHttpClient,
    proj_id: str,
    field: str,
    value_name: str,
) -> Optional[str]:
    """
    Resolve a human-readable field value (e.g. 'Minor', 'Open') to its Zoho ID string.
    Returns the ID string, or None if not found.
    """
    options = await get_field_options(client, proj_id, field)
    target = normalize(value_name)
    best, best_sc = None, 0
    for opt in options:
        opt_name = opt.get("name") or opt.get("type") or ""
        s = score(target, normalize(opt_name))
        if s > best_sc:
            best_sc, best = s, opt
    if best and best_sc >= 70:
        return str(best.get("id", ""))
    return None
