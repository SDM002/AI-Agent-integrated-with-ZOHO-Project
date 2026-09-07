"""Task write operation — delete a comment from a task (v3 DELETE API)."""
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, resolve_task, ok, err
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client


# Tool: Delete Task Comment
@tool
async def delete_task_comment(project_name: str, task_name: str, comment_id: str) -> str:
    """Delete a comment from a task in a Zoho project (v3 DELETE API).
    PREREQUISITE: Always call get_task_comments first to get the numeric comment_id.
    Never use comment text as the comment_id - only use the numeric ID from get_task_comments.
    Args:
        project_name: Project name (required).
        task_name: Task name (required).
        comment_id: Numeric comment ID from get_task_comments (required).
    """
    if not task_name:  return err("task_name is required.")
    if not comment_id: return err("comment_id is required.")

    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        proj = p_res["value"]

        t_res = await resolve_task(client, proj["id"], task_name)
        if not t_res["success"]: return err(t_res["user_message"])
        task = t_res["value"]
        task_id = str(task.get("id_string") or task.get("id", ""))

        res = await client.delete_v3(f"/projects/{proj['id']}/tasks/{task_id}/comments/{comment_id}")
        if not res["success"]: return err(res["user_message"])

        return ok({
            "comment_deleted": True,
            "comment_id":      comment_id,
            "task_name":       task["name"],
            "project":         proj["name"],
            "message":         f"Comment '{comment_id}' deleted from task '{task['name']}'.",
        })
