"""Timelog write operation create a new time log entry with office-hours enforcement."""
from typing import Optional
from datetime import datetime
from langchain_core.tools import tool
from app.tools.helpers import (
    resolve_project, resolve_task, normalize_date, format_hours, ok, err,
    resolve_user_by_email, fmt_12h, set_slot,
)
from app.tools.timelogs.get_timelogs_for_date import hhmm_to_12h
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client

# Tool: Create Time Log (Zoho v3 time logging with office-hours enforcement and slot conflict detection)
@tool
async def create_time_log(
    project_name: str,
    hours: float,
    owner_email: Optional[str] = None,
    task_name: Optional[str] = None,
    date: Optional[str] = None,
    notes: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    log_title: Optional[str] = None,
) -> str:
    """
    Log time worked in a Zoho project (general or task-specific).
    CRITICAL: Use this tool ONLY for a SINGLE time entry. If the user provides multiple time entries, DO NOT use this tool in a loop. You MUST use the tool designed for bulk adding time logs instead.
    PREREQUISITE: Always call get_timelogs_for_date first to check free slots and avoid conflicts.
    Args:
        project_name: Project name (required).
        hours: Hours worked 0-24 (required). E.g. 2 for 2 hours, 1.5 for 90 mins.
        owner_email: Email of the user logging time. Use the current user's email from context.
        task_name: Task name to log against. If not provided, logs as a General Log.
        date: Date YYYY-MM-DD or 'today'/'yesterday' (default: today).
        notes: Description of work done.
        start_time: Work start time in HH:MM 24hr format, e.g. '14:30'.
        end_time: Work end time in HH:MM 24hr format, e.g. '16:30'.
        log_title: Title for the log entry, particularly important for general logs.
    """
    if not project_name:  return err("project_name required.")
    if not hours or not 0 < hours <= 24: return err("hours must be between 0 and 24.")

    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        proj = p_res["value"]

        d_res = normalize_date(date)
        if d_res["success"]:
            mm, dd, yyyy = d_res["value"].split("-")
            v3_date = f"{yyyy}-{mm}-{dd}"
        else:
            v3_date = datetime.now().strftime("%Y-%m-%d")

        if start_time and end_time:
            def to_mins(t: str) -> int:
                p = t.strip().split(":")
                return int(p[0]) * 60 + (int(p[1]) if len(p) > 1 else 0)
            
            s_mins = to_mins(start_time)
            e_mins = to_mins(end_time)
            if e_mins <= s_mins:
                e_mins += 24 * 60
            
            slot_mins = e_mins - s_mins
            expected_mins = round(hours * 60)
            
            if abs(slot_mins - expected_mins) > 5:
                corr_e = (s_mins + expected_mins) % (24 * 60)
                corr_time = f"{corr_e//60:02d}:{corr_e%60:02d}"
                return ok({
                    "time_mismatch": True,
                    "error": f"Duration {slot_mins/60:.1f}h does not match requested {hours}h.",
                    "suggestion": f"For {hours}h starting at {start_time}, end at {corr_time}.",
                    "correct_end_time": corr_time
                })

        zoho_start = hhmm_to_12h(start_time) if start_time else None
        zoho_end   = hhmm_to_12h(end_time)   if end_time   else None

        target_task_id   = None
        target_task_name = "General Log"
        if task_name:
            t_res = await resolve_task(client, proj["id"], task_name, min_score=85)
            if t_res["success"]:
                raw_task = t_res["value"]
                task_id_found = raw_task["id"]
                detail_res = await client.get(f"/projects/{proj['id']}/tasks/{task_id_found}/")
                if not detail_res["success"]: return err(detail_res["user_message"])
                task_detail_list = detail_res["value"].get("tasks", [])
                is_closed = False
                if task_detail_list:
                    st = task_detail_list[0].get("status", {})
                    is_closed = (
                        (isinstance(st, dict) and (st.get("is_closed_type") or st.get("type", "") == "closed"))
                        or str(st).lower() in ("closed", "completed")
                    )
                if is_closed:
                    return err(
                        f"Task '{raw_task.get('name')}' is closed. "
                        f"You cannot log time to closed tasks. "
                        f"Please create a new task, or log without a task name (general)."
                    )
                target_task_id   = task_id_found
                target_task_name = raw_task["name"]
            else:
                return ok({
                    "task_not_found": True,
                    "task_name":      task_name,
                    "project":        proj["name"],
                    "options":        ["create_new_task", "create_in_folder", "general_log"],
                    "message": (
                        f"Task '{task_name}' does not exist in '{proj['name']}'. "
                        f"Options: (1) create it as a new task, "
                        f"(2) create it inside a specific folder/tasklist, "
                        f"(3) log without a task as a general log."
                    ),
                })

        owner_zpuid = None
        if owner_email:
            u_res = await resolve_user_by_email(client, owner_email)
            if u_res["success"]:
                owner_zpuid = u_res["value"].get("zpuid")

        is_general = target_task_id is None
        if is_general and not log_title:
            return ok({
                "needs_log_title": True,
                "project":         proj["name"],
                "message":         (
                    "A general time log requires a title (log_name). "
                    "Please ask the user: 'What should I call this general log?'"
                ),
            })

        # v3 JSON payload date YYYY-MM-DD, hours HH.MM (dot separator required by v3)
        v1_date = d_res["value"] if d_res["success"] else datetime.now().strftime("%m-%d-%Y")
        payload = {
            "log_name":    log_title or target_task_name or "General Log",
            "date":        v3_date,
            "bill_status": "Billable",
            "hours":       format_hours(hours).replace(":", "."),
        }
        if notes:       payload["notes"]       = notes
        if owner_zpuid: payload["owner_zpuid"] = owner_zpuid
        if zoho_start:  payload["start_time"]  = zoho_start
        if zoho_end:    payload["end_time"]    = zoho_end
        # module is always required by v3 use task id when available, else general
        payload["module"] = {"id": target_task_id, "type": "task"} if target_task_id else {"type": "general"}

        res = await client.post_v3(f"/projects/{proj['id']}/log", data=payload)

        if not res["success"]:
            msg = res["user_message"]
            if any(k in msg.lower() for k in ("closed", "log name is required")):
                return err(f"Zoho error: {msg}. Cannot log time to this task. Please log without a task name (general) or create a new task.")
            if any(k in msg.lower() for k in ("privilege", "permission", "access", "not allowed", "restrict", "forbidden", "unauthorized")):
                return ok({
                    "access_restricted": True,
                    "task":    target_task_name,
                    "project": proj["name"],
                    "message": msg,
                })
            return err(f"Zoho error: {msg}")

        tl = res["value"].get("timelogs", {})
        logs = tl.get("tasklogs", []) or tl.get("generallogs", [])
        log_id = str(logs[0].get("id_string") or logs[0].get("id", "")) if logs else ""

        # Update local slot cache for immediate availability check consistency
        if start_time and end_time:
            def to_m(t):
                p = t.split(":")
                return int(p[0]) * 60 + int(p[1])
            await set_slot(owner_email or "", v1_date, to_m(start_time), to_m(end_time), target_task_name)

        slot = f"{zoho_start} â€“ {zoho_end}" if (zoho_start and zoho_end) else None
        return ok({
            "logged":    True,
            "message":   f"Logged {hours}h to '{target_task_name}' in '{proj['name']}' on {v1_date}."
                         + (f" Time: {slot}." if slot else ""),
            "log_id":    log_id,
            "project":   proj["name"],
            "task":      target_task_name,
            "date":      v1_date,
            "hours":     hours,
            "time_slot": slot,
        })
