"""Task list read operation list all task list sections in a project."""
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, ok, err
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client

# Tool: List Task Lists
@tool
async def list_task_lists(project_name: str) -> str:
    """List all task list sections in a project. Args: project_name."""
    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        proj = p_res["value"]

        res = await client.get(f"/projects/{proj['id']}/tasklists/")
        if not res["success"]: return err(res["user_message"])
        tls = res["value"].get("tasklists", [])
        if not tls: return ok({"message": f"No task lists in '{proj['name']}'."})

        tasklists_list = []
        for tl in tls:
            tc = tl.get("task_count") or {}
            open_count = tc.get("open", 0) if isinstance(tc, dict) else 0
            closed_count = tc.get("closed", 0) if isinstance(tc, dict) else 0
            tasklists_list.append({
                "id": tl.get("id_string", tl.get("id")),
                "name": tl.get("name"),
                "position": tl.get("sequence", 0),
                "task_count": open_count + closed_count
            })

        return ok({"project": proj["name"], "tasklists": tasklists_list})

