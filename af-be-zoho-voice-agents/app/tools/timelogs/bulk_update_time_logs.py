"""Timelog write operation to update multiple time log entries in bulk using Zoho v3 APIs."""
from typing import List, Dict, Optional
from langchain_core.tools import tool
from app.tools.helpers import format_hours, ok, err
from app.tools.timelogs.get_timelogs_for_date import hhmm_to_12h
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client

@tool
async def bulk_update_time_logs(
    updates: List[Dict],
) -> str:
    """
    Update multiple time log entries in bulk (uses Zoho v3 bulk update API).
    Args:
        updates: A list of dictionaries representing log updates. Each dictionary must contain:
                 - 'log_id': Zoho numeric timelog ID (required)
                 - 'type': 'task' or 'general' (string, optional, defaults to 'general')
                 - 'hours': New hours worked (float, optional)
                 - 'notes': New notes (string, optional)
                 - 'start_time': New start time in HH:MM 24hr format (optional)
                 - 'end_time': New end time in HH:MM 24hr format (optional)
                 - 'project_name': Project name (optional)
    """
    if not updates:
        return err("No updates provided.")

    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        payload = []

        for idx, item in enumerate(updates):
            log_id = item.get("log_id")
            if not log_id:
                return err(f"Item {idx} requires 'log_id'.")

            # Guard: log_id must be numeric Zoho ID, not a task name or prefix like 'PA2-T3'
            if not str(log_id).strip().isdigit():
                return err(
                    f"Item {idx}: Invalid log_id '{log_id}'. The log_id must be the numeric Zoho log ID "
                    f"(e.g. '453093000000125045') from get_project_timelogs — "
                    f"not a task name, task prefix ID, or log title. "
                    f"Please call get_project_timelogs first to fetch the correct numeric log_id."
                )

            upd_item = {
                "id": str(log_id)
            }

            # Optional update fields
            if "hours" in item:
                try:
                    upd_item["hours"] = float(item["hours"])
                except Exception:
                    return err(f"Item {idx}: 'hours' must be a numeric value.")
            
            if "notes" in item:
                upd_item["notes"] = item["notes"]
            
            if "start_time" in item:
                upd_item["start_time"] = hhmm_to_12h(item["start_time"])
            if "end_time" in item:
                upd_item["end_time"] = hhmm_to_12h(item["end_time"])

            # Resolve module type
            log_type = item.get("type", "general").lower()
            if log_type not in ("task", "general"):
                log_type = "general"
            upd_item["module"] = log_type

            payload.append(upd_item)

        res = await client.patch_v3("/logs", data=payload)
        if not res["success"]:
            return err(res["user_message"])

        return ok({
            "updated": True,
            "count": len(payload),
            "message": f"Successfully updated {len(payload)} time logs in bulk."
        })
