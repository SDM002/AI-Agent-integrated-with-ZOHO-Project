"""Timelog write operation to create multiple time log entries in bulk using Zoho v3 APIs."""
import json
from datetime import datetime
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, resolve_task, normalize_date, format_hours, ok, err, resolve_user_by_email
from app.tools.timelogs.get_timelogs_for_date import hhmm_to_12h
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client

@tool
async def bulk_add_time_logs(
    logs_json: str,
    owner_email: Optional[str] = None,
) -> str:
    """
    Log MULTIPLE time entries in bulk (uses Zoho v3 bulk add API).
    CRITICAL: This is the ONLY tool you should use when the user's message contains more than one time entry to log. It handles validation and formatting for you.
    Args:
        logs_json: A JSON string containing a list of log dictionaries. Each dictionary must contain:
              - 'project_name': Name of project (string)
              - 'hours': Hours worked (float, e.g. 1.5)
              - 'type': 'task' or 'general' (string)
              - 'task_name': Task name (optional, only if type is 'task')
              - 'date': Date YYYY-MM-DD or today (optional)
              - 'notes': Work description (optional)
              - 'start_time': start time in HH:MM 24hr format (optional)
              - 'end_time': end time in HH:MM 24hr format (optional)
              - 'log_name': title of general log (optional)
        owner_email: Email of the user logging time. Use the current user's email from context.
    """
    print("--- BULK ADD TIME LOGS CALLED ---")
    print(f"RAW LOGS JSON: {logs_json}")
    try:
        logs = json.loads(logs_json)
    except Exception as e:
        print(f"JSON PARSE EXCEPTION: {e}")
        return err(f"Invalid JSON provided for logs_json: {e}")

    if not logs or not isinstance(logs, list):
        print("NOT A VALID LIST")
        return err("No logs provided or logs_json is not a valid list.")

    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        # Resolve owner ZPUID first (same across all logs in batch)
        owner_zpuid = None
        email_to_resolve = owner_email or user_id
        if email_to_resolve:
            first_proj_name = logs[0].get("project_name")
            if not first_proj_name:
                return err("Item 0 is missing 'project_name'.")
            p_res_first = await resolve_project(client, first_proj_name)
            if not p_res_first["success"]:
                return err(f"Item 0 project resolution failed: {p_res_first['user_message']}")
            
            u_res = await resolve_user_by_email(client, email_to_resolve, project_id=p_res_first["value"]["id"])
            if u_res["success"]:
                owner_zpuid = int(u_res["value"].get("zpuid"))
            else:
                return err(f"Failed to resolve user '{email_to_resolve}': {u_res['user_message']}")

        log_objects = []
        failed_items = []

        for idx, item in enumerate(logs):
            proj_name = item.get("project_name")
            if not proj_name:
                failed_items.append({"index": idx, "item": item, "reason": "Missing 'project_name'."})
                continue
            
            # Use cached first project or resolve
            if proj_name == first_proj_name:
                proj = p_res_first["value"]
            else:
                p_res = await resolve_project(client, proj_name)
                if not p_res["success"]:
                    failed_items.append({"index": idx, "item": item, "reason": p_res['user_message']})
                    continue
                proj = p_res["value"]

            # Parse hours as float
            try:
                hours_val = float(item.get("hours", 0))
            except Exception:
                failed_items.append({"index": idx, "item": item, "reason": "'hours' must be a numeric value."})
                continue

            # Parse date YYYY-MM-DD
            d_res = normalize_date(item.get("date"))
            if d_res["success"]:
                mm, dd, yyyy = d_res["value"].split("-")
                v3_date = f"{yyyy}-{mm}-{dd}"
            else:
                v3_date = datetime.now().strftime("%Y-%m-%d")

            log_type = item.get("type", "general").lower()
            
            log_item = {
                "project_id": int(proj["id"]),
                "log_name": item.get("log_name") or item.get("task_name") or "General Log",
                "type": log_type,
                "date": v3_date,
                "bill_status": "Billable",
                "hours": hours_val,
                "notes": item.get("notes") or "",
                "original_item": item  # Keep track for reporting
            }

            if owner_zpuid:
                log_item["owner_zpuid"] = owner_zpuid

            start_t = item.get("start_time")
            end_t = item.get("end_time")
            if start_t:
                log_item["start_time"] = hhmm_to_12h(start_t)
            if end_t:
                log_item["end_time"] = hhmm_to_12h(end_t)

            if log_type == "task":
                task_name = item.get("task_name")
                if not task_name:
                    failed_items.append({"index": idx, "item": item, "reason": "'task_name' is required when type is 'task'."})
                    continue
                t_res = await resolve_task(client, proj["id"], task_name, min_score=85)
                if not t_res["success"]:
                    failed_items.append({"index": idx, "item": item, "reason": f"Task '{task_name}' not found."})
                    continue
                log_item["item_id"] = int(t_res["value"]["id"])
            else:
                # Zoho v3 expects NO item_id or null for general logs
                pass

            log_objects.append(log_item)

        if not log_objects:
            return err(f"All {len(logs)} log entries failed validation. Reasons: {json.dumps(failed_items)}")

        # Prepare payload for API (remove 'original_item' which was just for tracking)
        api_payload = []
        for obj in log_objects:
            api_obj = obj.copy()
            api_obj.pop("original_item", None)
            api_payload.append(api_obj)

        # Send via multipart/form-data (required by addbulktimelogs)
        res = await client.send(
            "POST", 
            f"{client.v3_base_url}/addbulktimelogs", 
            files={"log_object": (None, json.dumps(api_payload))}
        )
        if not res["success"]:
            return err(res["user_message"])

        # Construct final success objects mapping to what was actually added
        successful_items = [obj["original_item"] for obj in log_objects]

        return ok({
            "added": True,
            "count": len(successful_items),
            "successful_items": successful_items,
            "failed_items": failed_items,
            "message": f"Successfully logged {len(successful_items)} time entries. {len(failed_items)} entries failed validation."
        })
