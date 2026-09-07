"""Bug write operation — remove a link between issues (v3 DELETE API)."""
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, ok, err, resolve_issue
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client


# Tool: Unlink Bugs
@tool
async def unlink_bugs(
    project_name: str,
    bug_title: str,
    link_id: str,
) -> str:
    """
    Remove a link between issues in a Zoho project (v3 DELETE API).
    PREREQUISITE: Always call get_linked_bugs first to obtain the numeric link_id.
    Never guess or invent a link_id.
    Args:
        project_name: Project name (required).
        bug_title: Title of the source issue (required).
        link_id: Numeric link ID to remove (from get_linked_bugs).
    """
    if not bug_title: return err("bug_title is required.")
    if not link_id:   return err("link_id is required.")

    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        proj = p_res["value"]

        src_id, src_title, src_err = await resolve_issue(client, proj["id"], bug_title)
        if src_err: return err(src_err)

        res = await client.delete_v3(f"/projects/{proj['id']}/issues/{src_id}/link/{link_id}")
        if not res["success"]: return err(res["user_message"])

        return ok({
            "unlinked":    True,
            "issue_title": src_title,
            "link_id":     link_id,
            "project":     proj["name"],
            "message":     f"Link '{link_id}' removed from issue '{src_title}'.",
        })
