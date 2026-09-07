"""Bug read operations — fetch the activity/audit timeline for a specific bug/issue (v3 API)."""
import re
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, local_time, ok, err, resolve_issue
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client


# Tool: Get Bug Activities
@tool
async def get_bug_activities(project_name: str, bug_title: str) -> str:
    """
    Fetch the activity/audit timeline for a specific issue in a Zoho project (v3 API).
    Shows who changed what and when — status changes, assignments, comments, etc.
    Args:
        project_name: Project name (required).
        bug_title: Title of the bug (required — used to locate it).
    """
    if not bug_title: return err("bug_title is required.")

    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        proj = p_res["value"]

        issue_id, found_title, issue_err = await resolve_issue(client, proj["id"], bug_title)
        if issue_err: return err(issue_err)

        # GET /api/v3/.../issues/{issueId}/activities?page=1&per_page=20&sort_by=ASC(created_time)
        res = await client.get_v3(
            f"/projects/{proj['id']}/issues/{issue_id}/activities",
            params={"page": 1, "per_page": 20, "sort_by": "ASC(created_time)"},
        )
        if not res["success"]: return err(res["user_message"])

        activities = res["value"].get("activities") or []

        if not activities:
            return ok({
                "issue_title": found_title,
                "project":     proj["name"],
                "activities":  [],
                "message":     f"No activities recorded for '{found_title}'.",
            })

        def clean_html(html_str):
            if not html_str: return ""
            return re.sub(r"<[^>]+>", "", html_str).strip()

        return ok({
            "issue_title": found_title,
            "project":     proj["name"],
            "count":       len(activities),
            "activities": [
                {
                    "time":   local_time(a.get("action_time") or a.get("time") or a.get("created_time", "")),
                    "actor":  a.get("user", {}).get("display_name") or a.get("user", {}).get("name") or (a.get("actor") or a.get("performed_by") or {}).get("name", "") if isinstance(a.get("actor") or a.get("performed_by") or a.get("user"), dict) else str(a.get("actor") or a.get("performed_by", "")),
                    "action": a.get("activity") or a.get("action") or a.get("event", ""),
                    "field":  (a.get("field") if isinstance(a.get("field"), dict) else {}).get("field_name") or a.get("field_name") or str(a.get("field") or ""),
                    "new_value": clean_html((a.get("field") if isinstance(a.get("field"), dict) else {}).get("new_value") or ""),
                }
                for a in activities
            ],
        })
