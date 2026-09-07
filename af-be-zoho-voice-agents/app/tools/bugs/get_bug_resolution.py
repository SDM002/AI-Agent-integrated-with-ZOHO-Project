"""Bug read operation — get the resolution for an issue (v3 API)."""
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, ok, err, resolve_issue
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client


# Tool: Get Bug Resolution
@tool
async def get_bug_resolution(project_name: str, bug_title: str) -> str:
    """
    Get the resolution for a bug/issue in a Zoho project (v3 API).
    Args:
        project_name: Project name (required).
        bug_title: Title of the issue (required).
    """
    if not bug_title: return err("bug_title is required.")

    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        proj = p_res["value"]

        issue_id, found_title, issue_err = await resolve_issue(client, proj["id"], bug_title)
        if issue_err: return err(issue_err)

        res = await client.get_v3(f"/projects/{proj['id']}/issues/{issue_id}/resolution")
        if not res["success"]: return err(res["user_message"])

        data = res["value"]
        issue_res = data.get("issue_resolution") or {}
        resolution_text = (
            issue_res.get("resolution")
            or issue_res.get("resolutionDsp")
            or data.get("resolution")
            or (data.get("resolutions") or [{}])[0].get("resolution", "")
        )
        if not resolution_text:
            return ok({"issue_title": found_title, "project": proj["name"], "resolution": None,
                       "message": f"No resolution found for '{found_title}'."})

        return ok({
            "issue_title": found_title,
            "project":     proj["name"],
            "resolution":  resolution_text,
        })
