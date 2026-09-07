"""Timelog write operation update an existing time log entry."""
import json
from typing import Optional
from langchain_core.tools import tool
from app.tools.helpers import (
    resolve_project, resolve_task, format_hours, ok, err,
)
from app.tools.timelogs.get_timelogs_for_date import hhmm_to_12h
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client

# Tool: Update Time Log
@tool
async def update_time_log(project_name: str, log_id: str, hours: Optional[float] = None,
                    notes: Optional[str] = None, task_name: Optional[str] = None,
                    task_id: Optional[str] = None,
                    start_time: Optional[str] = None, end_time: Optional[str] = None) -> str:
    """Update an existing time log entry.
    PREREQUISITE: Always call fetch_timelogs first to get the exact numeric log_id and task_id.
    Never guess or invent a log_id - use only the log_id returned by fetch_timelogs.
    Args:
        project_name: Project name (required).
        log_id: Numeric log ID from fetch_timelogs (required - never use task name or the string unknown).
        task_id: Task ID from fetch_timelogs result (pass when available).
        task_name: Task name (used only if task_id not available).
        hours: New hours value.
        notes: New notes/description.
        start_time: New start time in HH:MM 24hr format.
        end_time: New end time in HH:MM 24hr format.
    """
    if not project_name or not log_id: return err("project_name and log_id required.")
    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        proj = p_res["value"]

        payload = {}
        if hours:      payload["hours"]      = format_hours(hours).replace(":", ".")
        if notes:      payload["notes"]      = notes
        if start_time: payload["start_time"] = hhmm_to_12h(start_time)
        if end_time:   payload["end_time"]   = hhmm_to_12h(end_time)

        # module is ALWAYS required by v3 resolve from task_id > task_name > general
        resolved_task_id = task_id or None
        if not resolved_task_id and task_name:
            t_res = await resolve_task(client, proj["id"], task_name)
            if t_res["success"]:
                resolved_task_id = t_res["value"]["id"]
        module_obj = {"id": resolved_task_id, "type": "task"} if resolved_task_id else {"type": "general"}
        payload["module"] = json.dumps(module_obj)

        if len(payload) <= 1:  # only module set, nothing else to update
            return err("Provide at least one of: hours, notes, start_time, end_time.")

        # Fetch existing log to get previous values (try task first, then general)
        existing = {}
        try:
            prev_res = await client.get_v3(f"/projects/{proj['id']}/logs/{log_id}", params={"type": "task"})
            if not prev_res.get("success") or not prev_res.get("value"):
                prev_res = await client.get_v3(f"/projects/{proj['id']}/logs/{log_id}", params={"type": "general"})
            if prev_res.get("success"):
                raw_val = prev_res.get("value", {})
                if isinstance(raw_val, list):
                    existing = raw_val[0] if raw_val else {}
                elif isinstance(raw_val, dict):
                    existing = raw_val.get("log") or raw_val.get("timelog") or (raw_val.get("timelogs") or [{}])[0] or raw_val
        except Exception:
            pass

        res = await client.patch_v3(f"/projects/{proj['id']}/logs/{log_id}", data=payload)
        if not res["success"]: return err(res["user_message"])
        
        changes = []
        for key, new_val in payload.items():
            if key == "module": continue
            old_key = "log_hour" if key == "hours" else key
            old_val = existing.get(old_key, "Unknown")
            if key == "notes" and old_val and isinstance(old_val, str) and old_val.startswith("<div>"):
                import re
                old_val = re.sub(r'<[^>]*>', '', old_val).strip()
            changes.append({"field": key.replace("_", " ").title(), "previous_value": old_val, "new_value": new_val})

        return ok({
            "updated": True, 
            "log_id": log_id, 
            "changes": changes,
            "message": f"Time log {log_id} updated."
        })

