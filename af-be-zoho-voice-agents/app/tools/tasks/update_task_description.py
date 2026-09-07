"""Set or update the description of an existing task."""
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, resolve_task, ok, err
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client

# Tool: Update task description
@tool
async def update_task_description(project_name: str, task_name: str, description: str) -> str:
    """Set or update the description of an existing task. Args: project_name, task_name, description."""
    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        t_res = await resolve_task(client, p_res["value"]["id"], task_name)
        if not t_res["success"]: return err(t_res["user_message"])
        proj = p_res["value"]
        task = t_res["value"]

        v3_path = f"/projects/{proj['id']}/tasks/{task['id']}"
        prev_description = ""
        try:
            prev_res = await client.get_v3(v3_path)
            if prev_res["success"]:
                p_data = prev_res["value"].get("task") or prev_res["value"]
                prev_description = str(p_data.get("description") or "")
        except Exception:
            pass

        res = await client.patch_form(f"/projects/{proj['id']}/tasks/{task['id']}/", {"description": description})
        if not res["success"]: return err(res["user_message"])
        return ok({
            "updated": True,
            "task": task["name"],
            "project": proj["name"],
            "previous_description": prev_description,
            "new_description": description
        })
