"""Project read operation fetch full details of a single project."""
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, ok, err
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client

# Tool: Get Project Details
@tool
async def get_project_details(project_name: str) -> str:
    """Get full details of a project. Args: project_name."""
    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        res = await client.get(f"/projects/{p_res['value']['id']}/")
        if not res["success"]: return err(res["user_message"])
        projects = res["value"].get("projects", [])
        return ok(projects[0] if projects else {"message": "Not found."})
