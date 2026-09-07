"""Bug write operation — update the resolution of an issue (v3 PUT API)."""
from typing import Optional
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, resolve_field_id, ok, err, resolve_issue
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client


# Tool: Update Bug Resolution
@tool
async def update_bug_resolution(
    project_name: str,
    bug_title: str,
    resolution: str,
    status: Optional[str] = None,
) -> str:
    """
    Update the resolution of an issue in a Zoho project (v3 PUT API).
    Args:
        project_name: Project name (required).
        bug_title: Title of the issue (required).
        resolution: New resolution description text (required).
        status: Optional status name to set when updating resolution.
    """
    if not bug_title:  return err("bug_title is required.")
    if not resolution: return err("resolution text is required.")

    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        proj = p_res["value"]

        issue_id, found_title, issue_err = await resolve_issue(client, proj["id"], bug_title)
        if issue_err: return err(issue_err)

        payload: dict = {"resolution": resolution}
        if status:
            status_id = await resolve_field_id(client, proj["id"], "status", status)
            if status_id:
                payload["status_id"] = status_id

        res = await client.put_v3(f"/projects/{proj['id']}/issues/{issue_id}/resolution", data=payload)
        if not res["success"] and "500" in res.get("user_message", ""):
            res = await client.post_v3(f"/projects/{proj['id']}/issues/{issue_id}/resolution", data=payload)
        if not res["success"]: return err(res["user_message"])

        return ok({
            "resolution_updated": True,
            "issue_title":        found_title,
            "project":            proj["name"],
            "resolution":         resolution,
            "message":            f"Resolution updated for issue '{found_title}'.",
        })
