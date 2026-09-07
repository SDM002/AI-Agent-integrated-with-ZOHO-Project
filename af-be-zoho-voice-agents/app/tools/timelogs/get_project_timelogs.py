"""Timelog read operation to fetch bulk logs for a project using Zoho v3 APIs."""
import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, normalize_date, ok, err, resolve_user_by_email, parse_date_range
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client

@tool
async def get_project_timelogs(
    project_name: str,
    date: Optional[str] = None,
    owner_email: Optional[str] = None,
) -> str:
    """
    Fetch all time logs for a project (uses Zoho v3 API supporting date ranges, "this week", etc.).
    Args:
        project_name: Project name (required).
        date: Date YYYY-MM-DD, 'today', 'yesterday', or 'this week' (default: today).
        owner_email: Filter logs to this user's email.
    """
    if not project_name:
        return err("project_name is required.")

    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]:
            return err(p_res["user_message"])
        proj = p_res["value"]

        # Parse date range or single date
        start_date_str, end_date_str, is_week_view = parse_date_range(date)

        # Resolve owner ZPUID if email is provided
        owner_zpuid = None
        if owner_email:
            u_res = await resolve_user_by_email(client, owner_email, project_id=proj["id"])
            if u_res["success"]:
                owner_zpuid = u_res["value"].get("zpuid")

        # Query both task and general modules in parallel
        params = {
            "start_date": start_date_str,
            "end_date": end_date_str,
        }
        if owner_zpuid:
            params["users_list"] = str(owner_zpuid)

        async def fetch_module(module_type: str):
            p = {**params, "module": json.dumps({"type": module_type})}
            return await client.get_v3(f"/projects/{proj['id']}/timelogs", params=p)

        res_task, res_general = await asyncio.gather(
            fetch_module("task"),
            fetch_module("general")
        )

        logs = []
        
        def process_response(res, log_type):
            if not res["success"]:
                return
            for date_bucket in res["value"].get("time_logs", []):
                for raw in date_bucket.get("log_details", []):
                    # Filter by owner_zpuid if not filtered on server side
                    raw_owner_zpuid = raw.get("owner", {}).get("zpuid") or raw.get("added_by", {}).get("zpuid")
                    if owner_zpuid and str(raw_owner_zpuid or "") != str(owner_zpuid):
                        continue

                    task_detail = raw.get("module_detail", {})
                    task_name = task_detail.get("name") if log_type == "task" else "General"
                    log_title = raw.get("name") or task_detail.get("name") or "General Log"

                    # convert hours format "HH:MM" to friendly format including minutes
                    raw_hours = raw.get("log_hour", "0:00")
                    if ":" in raw_hours:
                        h, m = raw_hours.split(":", 1)
                        h, m = int(h), int(m)
                        if h > 0 and m > 0:
                            friendly_hours = f"{h} hr {m} min"
                        elif h > 0:
                            friendly_hours = f"{h} hr" if h == 1 else f"{h} hrs"
                        else:
                            friendly_hours = f"{m} min"
                    else:
                        friendly_hours = f"{raw_hours} hrs"

                    logs.append({
                        "log_id": str(raw.get("id", "")),
                        "type": log_type,
                        "task_id": str(task_detail.get("id", "")) if log_type == "task" else "",
                        "task_prefix_id": str(task_detail.get("prefix", "")) if log_type == "task" else "",
                        "task_name": task_name,
                        "log_title": log_title,
                        "hours": friendly_hours,
                        "date": raw.get("date", start_date_str),
                        "start_time": raw.get("start_time", ""),
                        "end_time": raw.get("end_time", ""),
                        "notes": raw.get("notes", ""),
                        "owner": raw.get("owner", {}).get("name", ""),
                        "billing_status": raw.get("billing_status", "Billable"),
                    })

        process_response(res_task, "task")
        process_response(res_general, "general")

        if not logs:
            return ok({
                "project": proj["name"],
                "date": date or start_date_str,
                "logs": [],
                "message": f"No time logs found in '{proj['name']}'."
            })

        return ok({
            "project": proj["name"],
            "date": date or start_date_str,
            "count": len(logs),
            "logs": logs
        })
