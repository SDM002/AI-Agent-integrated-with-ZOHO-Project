"""Task read operation — get full details of a single task (v3 API)."""
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, resolve_task, ok, err
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client


# Tool: Get Task Details
@tool
async def get_task_details(project_name: str, task_name: str) -> str:
    """
    Get full details of a specific task in a Zoho project (v3 API).
    Args:
        project_name: Project name (required).
        task_name: Task name (required).
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

        res = await client.get_v3(f"/projects/{proj['id']}/tasks/{task_id}")
        if not res["success"]: return err(res["user_message"])

        data = res["value"].get("task") or res["value"]
        owners_data = (
            data.get("owners_and_work", {}) or {}
        ).get("owners") or data.get("owners") or (data.get("details") or {}).get("owners") or []
        assignee_names = []
        if isinstance(owners_data, list):
            assignee_names = [o.get("name") or o.get("display_name", "") for o in owners_data if isinstance(o, dict)]
        elif isinstance(owners_data, dict):
            assignee_names = [owners_data.get("name") or owners_data.get("display_name", "")]

        return ok({
            "task_id":      task_id,
            "name":         data.get("name", ""),
            "status":       (data.get("status") or {}).get("name", "") if isinstance(data.get("status"), dict) else str(data.get("status", "")),
            "priority":     data.get("priority", ""),
            "start_date":   data.get("start_date", ""),
            "end_date":     data.get("end_date", ""),
            "description":  data.get("description", ""),
            "assignee":     assignee_names,
            "project":      proj["name"],
        })
