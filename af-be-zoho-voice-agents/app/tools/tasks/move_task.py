"""Task write operation — move a task to a different tasklist (v3 POST API)."""
from typing import Optional
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, resolve_task, resolve_tasklist, ok, err
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client


# Tool: Move Task
@tool
async def move_task(
    project_name: str,
    task_name: str,
    target_tasklist_name: Optional[str] = None,
) -> str:
    """
    Move a task to a different tasklist in a Zoho project (v3 POST API).
    Args:
        project_name: Project name (required).
        task_name: Name of the task to move (required).
        target_tasklist_name: Name of the target tasklist (optional, use '-' for default).
    """
    if not task_name: return err("task_name is required.")

    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        proj = p_res["value"]

        t_res = await resolve_task(client, proj["id"], task_name)
        if not t_res["success"]: return err(t_res["user_message"])
        task = t_res["value"]
        task_id = str(task.get("id_string") or task.get("id", ""))

        # Get previous tasklist
        prev_tasklist = "None"
        try:
            prev_res = await client.get_v3(f"/projects/{proj['id']}/tasks/{task_id}")
            if prev_res["success"]:
                p_data = prev_res["value"].get("task") or prev_res["value"]
                if isinstance(p_data.get("tasklist"), dict):
                    prev_tasklist = p_data["tasklist"].get("name") or "None"
        except Exception:
            pass

        target_tasklist_id = "-"
        if target_tasklist_name:
            tl_res = await resolve_tasklist(client, proj["id"], target_tasklist_name)
            if tl_res["success"]:
                target_tasklist_id = str(tl_res["value"]["id"])

        res = await client.post_v3(
            f"/projects/{proj['id']}/tasks/{task_id}/move",
            data={"target_tasklist_id": target_tasklist_id},
        )
        if not res["success"]: return err(res["user_message"])

        return ok({
            "moved":              True,
            "task_name":          task["name"],
            "previous_tasklist":  prev_tasklist,
            "target_tasklist":    target_tasklist_name or "default",
            "project":            proj["name"],
            "message":            f"Task '{task['name']}' moved to '{target_tasklist_name or 'default tasklist'}'.",
        })
