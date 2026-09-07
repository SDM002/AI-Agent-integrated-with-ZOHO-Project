"""Bug write operation — add a resolution to an issue (v3 POST API)."""
from typing import Optional
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, resolve_field_id, ok, err, resolve_issue
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client


# Tool: Add Bug Resolution
@tool
async def add_bug_resolution(
    project_name: str,
    bug_title: str,
    resolution: str,
    status: Optional[str] = None,
) -> str:
    """
    Add a resolution to an issue in a Zoho project (v3 POST API).
    Args:
        project_name: Project name (required).
        bug_title: Title of the issue (required).
        resolution: Resolution description text (required).
        status: Optional status name to set when resolving (e.g. 'Closed').
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

        # Get previous status and resolution
        prev_status = "None"
        prev_resolution = "None"
        try:
            prev_res = await client.get_v3(f"/projects/{proj['id']}/issues/{issue_id}")
            if prev_res["success"]:
                raw_val = prev_res["value"]
                p_data = raw_val[0] if isinstance(raw_val, list) and raw_val else (raw_val.get("issue") or (raw_val.get("issues") or [{}])[0] or {})
                prev_status = (p_data.get("status") or {}).get("name") if isinstance(p_data.get("status"), dict) else str(p_data.get("status") or "None")
        except Exception:
            pass

        try:
            prev_resol_res = await client.get_v3(f"/projects/{proj['id']}/issues/{issue_id}/resolution")
            if prev_resol_res["success"]:
                data = prev_resol_res["value"]
                issue_res = data.get("issue_resolution") or {}
                prev_resolution = issue_res.get("resolution") or issue_res.get("resolutionDsp") or data.get("resolution") or (data.get("resolutions") or [{}])[0].get("resolution") or "None"
        except Exception:
            pass

        payload: dict = {"resolution": resolution}
        if status:
            status_id = await resolve_field_id(client, proj["id"], "status", status)
            if status_id:
                payload["status_id"] = status_id

        res = await client.post_v3(f"/projects/{proj['id']}/issues/{issue_id}/resolution", data=payload)
        if not res["success"]: return err(res["user_message"])

        return ok({
            "resolution_added":   True,
            "issue_title":        found_title,
            "project":            proj["name"],
            "previous_status":    prev_status,
            "new_status":         status or prev_status,
            "previous_resolution": prev_resolution,
            "new_resolution":     resolution,
            "message":            f"Resolution added to issue '{found_title}'.",
        })
