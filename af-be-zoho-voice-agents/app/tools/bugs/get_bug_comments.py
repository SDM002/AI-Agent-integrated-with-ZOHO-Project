"""Bug read operation — list all comments on an issue (v3 API)."""
import re
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, local_time, ok, err, resolve_issue
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client


# Tool: Get Bug Comments
@tool
async def get_bug_comments(project_name: str, bug_title: str) -> str:
    """
    List all comments on a specific issue in a Zoho project (v3 API).
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

        res = await client.get_v3(f"/projects/{proj['id']}/issues/{issue_id}/comments")
        if not res["success"]: return err(res["user_message"])

        comments = res["value"].get("comments") or []
        if not comments:
            return ok({"issue_title": found_title, "project": proj["name"], "comments": [],
                       "message": f"No comments on '{found_title}'."})

        def clean_html(html_str):
            if not html_str: return ""
            return re.sub(r"<[^>]+>", "", html_str).strip()

        return ok({
            "issue_title": found_title,
            "project":     proj["name"],
            "count":       len(comments),
            "comments": [
                {
                    "comment_id": str(c.get("id", "")),
                    "comment":    clean_html(c.get("comment") or c.get("content", "")),
                    "author":     (c.get("added_by") or c.get("author") or c.get("created_by") or {}).get("name") or (c.get("added_by") or {}).get("full_name") or "Satyadeep Mohanta",
                    "time":       local_time(c.get("created_time") or c.get("last_modified_time") or c.get("time", "")),
                }
                for c in comments
            ],
        })
