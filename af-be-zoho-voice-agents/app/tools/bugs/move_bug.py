"""Bug write operations — move a bug/issue to a different project using the v3 API."""
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, ok, err, resolve_issue
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client


# Tool: Move Bug
@tool
async def move_bug(
    project_name: str,
    bug_title: str,
    target_project_name: str,
) -> str:
    """
    Move a bug/issue from one Zoho project to another (v3 API).
    Args:
        project_name: Source project name (required).
        bug_title: Title of the bug to move (required).
        target_project_name: Destination project name (required).
    """
    if not bug_title: return err("bug_title is required.")

    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        proj = p_res["value"]

        tp_res = await resolve_project(client, target_project_name)
        if not tp_res["success"]: return err(tp_res["user_message"])
        target_proj = tp_res["value"]

        issue_id, found_title, issue_err = await resolve_issue(client, proj["id"], bug_title)
        if issue_err: return err(issue_err)

        # POST /api/v3/.../issues/{issueId}/move  →  body: {"to_project": "<target_project_id>"}
        res = await client.post_v3(
            f"/projects/{proj['id']}/issues/{issue_id}/move",
            data={"to_project": target_proj["id"]},
        )
        if not res["success"]: return err(res["user_message"])

        return ok({
            "moved":        True,
            "issue_id":     issue_id,
            "issue_title":  found_title,
            "from_project": proj["name"],
            "to_project":   target_proj["name"],
            "message":      f"Issue '{found_title}' moved from '{proj['name']}' to '{target_proj['name']}'.",
        })
