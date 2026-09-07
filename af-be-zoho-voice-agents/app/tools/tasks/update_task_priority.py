"""Update the priority of a task."""
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, resolve_task, ok, err
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client

# Tool: Update task priority
@tool
async def update_task_priority(project_name: str, task_name: str, priority: str) -> str:
    """Update task priority. Args: project_name, task_name, priority (none|low|medium|high)."""
    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        t_res = await resolve_task(client, p_res["value"]["id"], task_name)
        if not t_res["success"]: return err(t_res["user_message"])
        proj = p_res["value"]
        task = t_res["value"]

        v3_path = f"/projects/{proj['id']}/tasks/{task['id']}"
        prev_priority = "None"
        try:
            prev_res = await client.get_v3(v3_path)
            if prev_res["success"]:
                p_data = prev_res["value"].get("task") or prev_res["value"]
                prev_priority = str(p_data.get("priority", "none")).title()
        except Exception:
            pass

        res = await client.patch_form(f"/projects/{proj['id']}/tasks/{task['id']}/", data={"priority": priority.title()})
        if not res["success"]: return err(res["user_message"])
        return ok({
            "updated": True,
            "task": task["name"],
            "project": proj["name"],
            "previous_priority": prev_priority,
            "new_priority": priority.title()
        })
