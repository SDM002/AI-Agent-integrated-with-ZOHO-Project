"""Task write operation — update an existing comment on a task (v3 PATCH API)."""
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, resolve_task, ok, err
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client


# Tool: Update Task Comment
@tool
async def update_task_comment(
    project_name: str,
    task_name: str,
    comment_id: str,
    comment: str,
) -> str:
    """
    Update an existing comment on a task in a Zoho project (v3 PATCH API).
    Args:
        project_name: Project name (required).
        task_name: Task name (required).
        comment_id: ID of the comment to update (from get_task_comments).
        comment: New comment text (required).
    """
    if not task_name:  return err("task_name is required.")
    if not comment_id: return err("comment_id is required.")
    if not comment:    return err("comment text is required.")

    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        proj = p_res["value"]

        t_res = await resolve_task(client, proj["id"], task_name)
        if not t_res["success"]: return err(t_res["user_message"])
        task = t_res["value"]
        task_id = str(task.get("id_string") or task.get("id", ""))

        prev_comment = "None"
        try:
            prev_res = await client.get_v3(f"/projects/{proj['id']}/tasks/{task_id}/comments")
            if prev_res["success"]:
                comments_list = prev_res["value"].get("comments") or []
                for c in comments_list:
                    if str(c.get("id")) == str(comment_id):
                        prev_comment = c.get("comment") or c.get("content") or "None"
                        break
        except Exception:
            pass

        res = await client.patch_v3(
            f"/projects/{proj['id']}/tasks/{task_id}/comments/{comment_id}",
            data={"comment": comment},
        )
        if not res["success"]: return err(res["user_message"])

        return ok({
            "comment_updated":    True,
            "comment_id":         comment_id,
            "task_name":          task["name"],
            "project":            proj["name"],
            "previous_comment":   prev_comment,
            "new_comment":        comment,
            "message":            f"Comment updated on task '{task['name']}'.",
        })
