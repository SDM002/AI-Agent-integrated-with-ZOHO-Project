"""Delete a task permanently from a project."""
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, resolve_task, ok, err
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client

# Tool: Delete a task
@tool
async def delete_task(project_name: str, task_name: str) -> str:
    """Delete a task permanently. ALWAYS confirm with user first. Args: project_name, task_name."""
    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        t_res = await resolve_task(client, p_res["value"]["id"], task_name)
        if not t_res["success"]: return err(t_res["user_message"])
        proj = p_res["value"]
        task = t_res["value"]

        res = await client.delete(f"/projects/{proj['id']}/tasks/{task['id']}/")
        if not res["success"]: return err(res["user_message"])
        return ok({"deleted": True, "task": task["name"]})
