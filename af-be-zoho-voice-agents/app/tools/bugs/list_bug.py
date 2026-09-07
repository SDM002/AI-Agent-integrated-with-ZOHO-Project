"""Bug read operations — list bugs/issues in a project using the v3 API."""
from typing import Optional
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, ok, err
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client


# Tool: List Project Bugs
@tool
async def list_project_bugs(
    project_name: str,
    status_filter: Optional[str] = None,
    per_page: int = 50,
) -> str:
    """
    List bugs/issues in a Zoho project (v3 API).
    Args:
        project_name: Project name (required).
        status_filter: Optional status name to filter e.g. 'Open', 'Closed', 'In progress'.
        per_page: Number of issues to return (default 50, max 100).
    """
    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        proj = p_res["value"]

        params: dict = {
            "page":     1,
            "per_page": min(per_page, 100),
            "sort_by":  "ASC(created_time)",
        }

        res = await client.get_v3(f"/projects/{proj['id']}/issues", params=params)
        if not res["success"]: return err(res["user_message"])

        issues = res["value"].get("issues") or res["value"].get("bugs") or []

        # Client-side status filter (v3 status filter requires a status ID; name filter is simpler)
        if status_filter:
            sf = status_filter.strip().lower()
            issues = [
                iss for iss in issues
                if sf in str(
                    (iss.get("status") or {}).get("name", "")
                    if isinstance(iss.get("status"), dict)
                    else iss.get("status", "")
                ).lower()
            ]

        if not issues:
            return ok({
                "project": proj["name"],
                "count":   0,
                "message": f"No issues found in '{proj['name']}'."
                           + (f" (filter: {status_filter})" if status_filter else ""),
            })

        return ok({
            "project": proj["name"],
            "count":   len(issues),
            "issues": [
                {
                    "id":       str(iss.get("id", "")),
                    "name":     iss.get("name") or iss.get("title", ""),
                    "status":   (iss.get("status") or {}).get("name", "") if isinstance(iss.get("status"), dict) else str(iss.get("status", "")),
                    "severity": (iss.get("severity") or {}).get("value") or (iss.get("severity") or {}).get("name", "") if isinstance(iss.get("severity"), dict) else str(iss.get("severity", "")),
                    "assignee": (iss.get("assignee") or {}).get("name", "") if isinstance(iss.get("assignee"), dict) else "",
                }
                for iss in issues
            ],
        })
