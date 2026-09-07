"""Bug write operation — update an existing comment on an issue (v3 PATCH API)."""
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, ok, err, resolve_issue
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client


# Tool: Update Bug Comment
@tool
async def update_bug_comment(
    project_name: str,
    bug_title: str,
    comment_id: str,
    comment: str,
) -> str:
    """
    Update an existing comment on an issue in a Zoho project (v3 PATCH API).
    PREREQUISITE: Always call get_bug_comments first to obtain the numeric comment_id.
    Never guess or invent a comment_id.
    Args:
        project_name: Project name (required).
        bug_title: Title of the issue (required).
        comment_id: Numeric ID of the comment to update (from get_bug_comments).
        comment: New comment text (required).
    """
    if not bug_title:  return err("bug_title is required.")
    if not comment_id: return err("comment_id is required.")
    if not comment:    return err("comment text is required.")

    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        proj = p_res["value"]

        issue_id, found_title, issue_err = await resolve_issue(client, proj["id"], bug_title)
        if issue_err: return err(issue_err)

        res = await client.patch_v3(
            f"/projects/{proj['id']}/issues/{issue_id}/comments/{comment_id}",
            data={"comment": comment},
        )
        if not res["success"]: return err(res["user_message"])

        return ok({
            "comment_updated": True,
            "comment_id":      comment_id,
            "issue_title":     found_title,
            "project":         proj["name"],
            "message":         f"Comment updated on issue '{found_title}'.",
        })
