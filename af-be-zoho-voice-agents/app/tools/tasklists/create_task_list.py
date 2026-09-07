"""Task list write operation create a new task list (folder) inside a project."""
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, ok, err
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client

# Tool: Create Task List
@tool
async def create_task_list(project_name: str, tasklist_name: str) -> str:
    """Create a new task list (folder) in a project. Args: project_name, tasklist_name."""
    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        proj = p_res["value"]

        res = await client.post_form(f"/projects/{proj['id']}/tasklists/", data={"name": tasklist_name, "flag": "internal"})
        if not res["success"]: return err(res["user_message"])
        return ok({"created": True, "project": proj["name"], "tasklist": tasklist_name,
                   "message": f"Created task list '{tasklist_name}' in '{proj['name']}'."})
