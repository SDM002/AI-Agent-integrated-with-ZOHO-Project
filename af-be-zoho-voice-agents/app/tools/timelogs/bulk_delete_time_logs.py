"""Timelog write operation to delete multiple time log entries in bulk using Zoho v3 APIs."""
from typing import List, Dict
from langchain_core.tools import tool
from app.tools.helpers import ok, err
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client

@tool
async def bulk_delete_time_logs(
    logs_to_delete: List[Dict],
) -> str:
    """
    Delete multiple time logs in bulk (uses Zoho v3 bulk delete API).
    ALWAYS confirm with the user before deleting logs.
    Args:
        logs_to_delete: A list of dictionaries representing logs to delete. Each dictionary must contain:
                        - 'log_id': Zoho numeric log ID (required)
                        - 'type': 'task' or 'general' (string, optional, default: 'general')
                        - 'project_name': Project name (optional)
    """
    if not logs_to_delete:
        return err("No logs specified for deletion.")

    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        payload = []
        for idx, item in enumerate(logs_to_delete):
            log_id = item.get("log_id")
            if not log_id:
                return err(f"Item {idx} is missing 'log_id'.")

            # Guard: log_id must be numeric Zoho ID, not a task name or prefix like 'PA2-T3'
            if not str(log_id).strip().isdigit():
                return err(
                    f"Item {idx}: Invalid log_id '{log_id}'. The log_id must be the numeric Zoho log ID "
                    f"(e.g. '453093000000129001') from get_project_timelogs — "
                    f"not a task name, task prefix ID, or log title. "
                    f"Please call get_project_timelogs first to fetch the correct numeric log_id."
                )
            
            log_type = item.get("type", "general").lower()
            if log_type not in ("task", "general"):
                log_type = "general"

            payload.append({
                "id": str(log_id),
                "module": log_type
            })

        res = await client.delete_v3("/timelogs/bulkdelete", data=payload)
        if not res["success"]:
            return err(res["user_message"])

        return ok({
            "deleted": True,
            "count": len(logs_to_delete),
            "message": f"Successfully deleted {len(logs_to_delete)} time logs in bulk."
        })
