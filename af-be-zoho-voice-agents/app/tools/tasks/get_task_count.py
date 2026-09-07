"""Task read operation — get task count for a project (v3 API)."""
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, ok, err
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client


# Tool: Get Task Count
@tool
async def get_task_count(project_name: str) -> str:
    """
    Get the total task count for a Zoho project (v3 API).
    Args:
        project_name: Project name (required).
    """
    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        proj = p_res["value"]

        res = await client.get_v3(f"/projects/{proj['id']}/tasks/count")
        if not res["success"]: return err(res["user_message"])

        data = res["value"]
        return ok({
            "project": proj["name"],
            "count":   data.get("count") or data.get("task_count") or 0,
        })
