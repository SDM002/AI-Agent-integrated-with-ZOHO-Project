"""Bug write operation — delete a comment from an issue (v3 DELETE API)."""
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, ok, err, resolve_issue
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client


# Tool: Delete Bug Comment
@tool
async def delete_bug_comment(project_name: str, bug_title: str, comment_id: str) -> str:
    """Delete a comment from an issue in a Zoho project (v3 DELETE API).
    PREREQUISITE: Always call get_bug_comments first to get the numeric comment_id.
    Never use comment text as the comment_id - only use the numeric ID from get_bug_comments.
    Args:
        project_name: Project name (required).
        bug_title: Title of the issue (required).
        comment_id: Numeric comment ID from get_bug_comments (required).
    """
    if not bug_title:  return err("bug_title is required.")
    if not comment_id: return err("comment_id is required.")

    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        proj = p_res["value"]

        issue_id, found_title, issue_err = await resolve_issue(client, proj["id"], bug_title)
        if issue_err: return err(issue_err)

        res = await client.delete_v3(f"/projects/{proj['id']}/issues/{issue_id}/comments/{comment_id}")
        if not res["success"]: return err(res["user_message"])

        return ok({
            "comment_deleted": True,
            "comment_id":      comment_id,
            "issue_title":     found_title,
            "project":         proj["name"],
            "message":         f"Comment '{comment_id}' deleted from issue '{found_title}'.",
        })
