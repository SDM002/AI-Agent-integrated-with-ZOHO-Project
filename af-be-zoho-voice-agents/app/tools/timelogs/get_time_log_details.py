"""Timelog read operation to fetch details of a single time log entry."""
from typing import Optional
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, ok, err
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client

@tool
async def get_time_log_details(
    project_name: str,
    log_id: str,
    log_type: Optional[str] = "task",
) -> str:
    """
    Fetch the details of a specific single time log entry by its unique log ID.
    Args:
        project_name: Project name (required).
        log_id: Unique timelog ID (required).
        log_type: Type of log: 'task' or 'general' (default: 'task').
    """
    if not project_name or not log_id:
        return err("project_name and log_id are required.")

    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]:
            return err(p_res["user_message"])
        proj = p_res["value"]

        params = {"type": log_type}
        res = await client.get_v3(f"/projects/{proj['id']}/logs/{log_id}", params=params)
        if not res["success"]:
            return err(res["user_message"])
        
        return ok(res["value"])
