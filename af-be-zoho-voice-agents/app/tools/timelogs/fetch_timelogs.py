"""Timelog read operation fetch full log list for a project and date."""
import asyncio
from typing import Optional
from datetime import datetime
from langchain_core.tools import tool
from app.tools.helpers import (
    resolve_project, normalize_date, ok, err,
    resolve_user_by_email,
)
from app.utils.request_context import get_user_id, get_request_context
from app.services.zoho.client_factory import build_zoho_client

# Tool: Fetch Time Logs (full log list for a project and date)
@tool
async def fetch_timelogs(
    project_name: str,
    date: Optional[str] = None,
    owner_email: Optional[str] = None,
) -> str:
    """Fetch all time logs for a project. Args: project_name, date (YYYY-MM-DD or today), owner_email. If the user says 'me' or implies themselves, use the current user's email from context."""
    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        proj = p_res["value"]

        is_week_view = False
        if date and "week" in date.lower():
            is_week_view = True
            clean_date = date.lower().replace("this week", "").replace("week of", "").replace("week", "").strip()
            if clean_date:
                d_res = normalize_date(clean_date)
                log_date = d_res["value"] if d_res["success"] else datetime.now().strftime("%m-%d-%Y")
            else:
                log_date = datetime.now().strftime("%m-%d-%Y")
        else:
            d_res = normalize_date(date)
            log_date = d_res["value"] if d_res["success"] else datetime.now().strftime("%m-%d-%Y")

        owner_zpuid = None
        if owner_email:
            u_res = await resolve_user_by_email(client, owner_email, project_id=proj["id"])
            if u_res["success"]:
                owner_zpuid = u_res["value"].get("zpuid")

        if not owner_zpuid:
            ctx = get_request_context()
            tag = "[Current user's email:"
            s = ctx.find(tag)
            if s != -1:
                rest = ctx[s + len(tag):]
                e = rest.find("]")
                if e != -1:
                    fallback_email = rest[:e].strip()
                    u_res = await resolve_user_by_email(client, fallback_email, project_id=proj["id"])
                    if u_res["success"]:
                        owner_zpuid = u_res["value"].get("zpuid")

        owner_name_filter = ""
        if owner_email:
            u_res = await resolve_user_by_email(client, owner_email, project_id=proj["id"])
            if u_res["success"]:
                owner_name_filter = u_res["value"].get("name", "").lower()

        def keep(raw) -> bool:
            if not owner_name_filter: return True
            return owner_name_filter in raw.get("owner_name", "").lower()

        def build_log(raw, log_type) -> dict:
            task_info = raw.get("task", {}) if isinstance(raw.get("task"), dict) else {}
            title = raw.get("name") or raw.get("notes") or "General Log"
            return {
                "log_id":         str(raw.get("id_string") or raw.get("id", "")),
                "type":           log_type,
                "task_id":        str(task_info.get("id_string") or task_info.get("id", "")),
                "task_name":      task_info.get("name") or raw.get("taskname", "") if log_type == "task" else "General",
                "log_title":      title,
                "hours":          raw.get("hours_display") or raw.get("hours", ""),
                "date":           raw.get("log_date", log_date),
                "start_time":     raw.get("start_time", ""),
                "end_time":       raw.get("end_time", ""),
                "notes":          raw.get("notes", ""),
                "owner":          raw.get("owner_name", ""),
                "billing_status": raw.get("billing_status") or raw.get("bill_status", "Billable"),
            }

        logs = []
        seen_ids = set()

        def add(raw, log_type) -> None:
            raw_date = raw.get("log_date", "")
            if not is_week_view:
                if raw_date and raw_date != log_date: return
            if not keep(raw): return
            entry = build_log(raw, log_type)
            entry["date"] = raw_date or log_date
            if entry["log_id"] and entry["log_id"] not in seen_ids:
                seen_ids.add(entry["log_id"])
                logs.append(entry)

        # Zoho API /logs/ requires users_list, view_type, date, and component_type
        params = {
            "date": log_date,
            "view_type": "week" if is_week_view else "day",
            "users_list": "all",
            "bill_status": "All"
        }
        types = ["general", "task", "bug"]
        api_tasks = [
            client.get(f"/projects/{proj['id']}/logs/", params={**params, "component_type": t})
            for t in types
        ]
        results = await asyncio.gather(*api_tasks)

        for res, log_type in zip(results, types):
            if res["success"]:
                tl = res["value"].get("timelogs", {})
                raw_list = []
                if "date" in tl:
                    for date_obj in tl.get("date", []):
                        if log_type == "general":
                            raw_list.extend(date_obj.get("generallogs", []))
                        elif log_type == "task":
                            raw_list.extend(date_obj.get("tasklogs", []))
                        elif log_type == "bug":
                            raw_list.extend(date_obj.get("buglogs", []) or date_obj.get("tasklogs", []))
                else:
                    if log_type == "general":
                        raw_list = tl.get("generallogs", [])
                    elif log_type == "task":
                        raw_list = tl.get("tasklogs", [])
                    elif log_type == "bug":
                        raw_list = tl.get("buglogs", []) or tl.get("tasklogs", [])
                
                for raw in raw_list:
                    add(raw, log_type)

        if not logs:
            return ok({"project": proj["name"], "date": log_date, "logs": [],
                       "message": f"No time logs found in '{proj['name']}' for {log_date}."})
        return ok({"project": proj["name"], "date": log_date, "count": len(logs), "logs": logs})
