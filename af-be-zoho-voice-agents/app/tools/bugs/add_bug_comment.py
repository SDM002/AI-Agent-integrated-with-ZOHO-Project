"""Bug write operation — add a comment to an issue (v3 POST API)."""
from typing import Optional, List
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, ok, err, resolve_issue
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client


# Tool: Add Bug Comment
@tool
async def add_bug_comment(
    project_name: str,
    bug_title: str,
    comment: str,
    notify_users: Optional[List[str]] = None,
) -> str:
    """
    Add a comment to an issue in a Zoho project (v3 POST API).
    Args:
        project_name: Project name (required).
        bug_title: Title of the issue (required).
        comment: Comment text (required).
        notify_users: Optional list of user zpuids to notify.
    """
    if not bug_title: return err("bug_title is required.")
    if not comment:   return err("comment text is required.")

    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        proj = p_res["value"]

        issue_id, found_title, issue_err = await resolve_issue(client, proj["id"], bug_title)
        if issue_err: return err(issue_err)

        payload: dict = {"comment": comment}
        if notify_users:
            payload["notify_users"] = notify_users

        res = await client.post_v3(f"/projects/{proj['id']}/issues/{issue_id}/comments", data=payload)
        if not res["success"]: return err(res["user_message"])

        created = res["value"].get("comment") or (res["value"].get("comments") or [{}])[0]
        comment_id = str(created.get("id", ""))

        return ok({
            "comment_added": True,
            "comment_id":    comment_id,
            "issue_title":   found_title,
            "project":       proj["name"],
            "message":       f"Comment added to issue '{found_title}'.",
        })
