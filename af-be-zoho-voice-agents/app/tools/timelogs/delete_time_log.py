"""Timelog write operation delete a time log entry with v3, v1 fallback."""
from typing import Optional
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, ok, err
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client

# Tool: Delete Time Log (tries v3 first, falls back to v1 task-level and project-level paths)
@tool
async def delete_time_log(project_name: str, log_id: str, task_id: Optional[str] = None) -> str:
    """Delete a time log.ALWAYS confirm with user first. Args: project_name, log_id (required), task_id (pass when available from fetch result)."""
    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        proj = p_res["value"]

        # Guard: log_id must be a numeric Zoho ID, not a task name or task prefix
        if not str(log_id).strip().isdigit():
            return err(
                f"Invalid log_id '{log_id}'. The log_id must be the numeric Zoho log ID "
                f"(e.g. '453093000000129001') from get_project_timelogs — "
                f"not a task name, task prefix ID, or log title. "
                f"Please call get_project_timelogs first to fetch the correct numeric log_id."
            )

        # v3 DELETE â€” module must be an object, not a string
        module_obj = (
            {"id": task_id, "type": "task"} if task_id
            else {"type": "general"}
        )
        res = await client.delete_v3(f"/projects/{proj['id']}/logs/{log_id}", data={"module": module_obj})

        if not res["success"]:
            # v1 fallback: task-specific path first, then project-level general log path
            if task_id:
                res = await client.delete(f"/projects/{proj['id']}/tasks/{task_id}/logs/{log_id}/")
            if not res["success"]:
                res = await client.delete(f"/projects/{proj['id']}/logs/{log_id}/")

        if not res["success"]: return err(res["user_message"])
        return ok({"deleted": True, "log_id": log_id, "message": f"Time log {log_id} deleted from '{proj['name']}'."})
