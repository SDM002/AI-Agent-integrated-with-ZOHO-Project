"""Daily timelog summary across all active projects for the current user."""
from datetime import datetime
from typing import Optional

from langchain_core.tools import tool

from app.services.zoho.client_factory import build_zoho_client
from app.tools.helpers import (
    err,
    extract_slot_from_notes,
    fmt_12h,
    normalize_date,
    ok,
    parse_12h_to_mins,
    parse_hhmm,
    resolve_user_by_email,
)
from app.tools.timelogs.get_timelogs_for_date import office_bounds
from app.utils.request_context import get_request_context, get_user_id


def _current_user_email_from_context() -> str:
    ctx = get_request_context()
    tag = "[Current user's email:"
    start = ctx.find(tag)
    if start == -1:
        return ""
    rest = ctx[start + len(tag):]
    end = rest.find("]")
    return rest[:end].strip() if end != -1 else ""


def _log_owner_matches(raw: dict, owner_zpuid: Optional[str]) -> bool:
    if not owner_zpuid:
        return True
    owner = raw.get("owner", {})
    owner_dict = owner if isinstance(owner, dict) else {}
    raw_owner = raw.get("owner_zpuid") or raw.get("zpuid") or owner_dict.get("zpuid")
    return str(raw_owner or "") == str(owner_zpuid)


def _iter_timelog_rows(payload: dict) -> list[dict]:
    timelogs = payload.get("timelogs", {})
    rows = []

    for key in ("tasklogs", "generallogs", "buglogs"):
        rows.extend(timelogs.get(key, []))

    for day_bucket in timelogs.get("date", []):
        if not isinstance(day_bucket, dict):
            continue
        for key in ("tasklogs", "generallogs", "buglogs"):
            rows.extend(day_bucket.get(key, []))

    return rows


@tool
async def get_daily_timelog_summary(
    date: Optional[str] = None,
    owner_email: Optional[str] = None,
) -> str:
    """
    Fetch the current user's time logs across all active projects for one date.

    Use this when the user asks for total logged time, or their time logs
    for a specific day without naming a single project.
    Args:
        date: Date YYYY-MM-DD, MM-DD-YYYY, 'today', or 'yesterday'. Defaults to today.
        owner_email: Current user's email. If omitted or if the user says 'me' or implies themselves, the request context email is used.
    """
    office_start, office_end = office_bounds()

    d_res = normalize_date(date)
    log_date = d_res["value"] if d_res["success"] else datetime.now().strftime("%m-%d-%Y")

    email = (owner_email or _current_user_email_from_context()).strip()

    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        owner_zpuid = None
        if email:
            u_res = await resolve_user_by_email(client, email)
            if u_res["success"]:
                owner_zpuid = u_res["value"].get("zpuid")

        timed_intervals = []
        total_logged_hours = 0.0
        untimed_hours = 0.0
        logs = []
        project_names = set()
        seen_ids = set()

        for component_type in ("task", "general", "bug"):
            params = {
                "users_list": owner_zpuid or "all",
                "view_type": "day",
                "date": log_date,
                "bill_status": "All",
                "component_type": component_type,
                "approval_status": "all",
                "index": 0,
                "range": 200,
            }

            res = await client.get("/logs", params=params)
            if not res["success"]:
                return err(res["user_message"])

            for raw in _iter_timelog_rows(res["value"]):
                log_id = str(raw.get("id_string") or raw.get("id", ""))
                if log_id and log_id in seen_ids:
                    continue
                if log_id:
                    seen_ids.add(log_id)

                if raw.get("log_date") and raw["log_date"] != log_date:
                    continue
                if not _log_owner_matches(raw, owner_zpuid):
                    continue

                hours_text = raw.get("hours", "0") or raw.get("hours_display", "0")
                start_text = raw.get("start_time") or raw.get("from_time")
                end_text = raw.get("end_time") or raw.get("to_time")
                task_info = raw.get("task", {}) if isinstance(raw.get("task"), dict) else {}
                bug_info = raw.get("bug", {}) if isinstance(raw.get("bug"), dict) else {}
                project_info = raw.get("project", {}) if isinstance(raw.get("project"), dict) else {}
                project_name = (
                    project_info.get("name")
                    or raw.get("project_name")
                    or raw.get("project")
                    or ""
                )
                if project_name:
                    project_names.add(str(project_name))
                task_name = (
                    task_info.get("name")
                    or bug_info.get("name")
                    or raw.get("taskname")
                    or raw.get("name")
                    or "General"
                )
                duration = parse_hhmm(hours_text)
                total_logged_hours += duration

                start_mins = parse_12h_to_mins(start_text) if start_text else None
                end_mins = parse_12h_to_mins(end_text) if end_text else None

                if start_mins is not None and end_mins is not None:
                    if start_mins < end_mins:
                        timed_intervals.append((start_mins, end_mins, project_name, task_name))
                else:
                    slot_from_notes = extract_slot_from_notes(raw.get("notes") or "")
                    if slot_from_notes:
                        note_start, note_end = slot_from_notes
                        if note_start < note_end:
                            timed_intervals.append((note_start, note_end, project_name, task_name))
                    else:
                        untimed_hours += duration

                logs.append({
                    "project": project_name,
                    "log_id": log_id,
                    "task": task_name,
                    "hours": hours_text,
                    "start_time": start_text,
                    "end_time": end_text,
                    "approval_status": raw.get("approval_status") or raw.get("approval", ""),
                })

        timed_intervals.sort(key=lambda item: item[0])
        merged = []
        for start, end, project_name, task_name in timed_intervals:
            if merged and start <= merged[-1][1]:
                merged[-1] = (
                    merged[-1][0],
                    max(merged[-1][1], end),
                    merged[-1][2],
                )
            else:
                merged.append((start, end, [{"project": project_name, "task": task_name}]))

        free_slots = []
        cursor = office_start
        for start, end, _ in merged:
            if cursor < start:
                free_slots.append({
                    "start": fmt_12h(cursor),
                    "end": fmt_12h(start),
                    "duration_hours": round((start - cursor) / 60, 2),
                })
            cursor = max(cursor, end)
        if cursor < office_end:
            free_slots.append({
                "start": fmt_12h(cursor),
                "end": fmt_12h(office_end),
                "duration_hours": round((office_end - cursor) / 60, 2),
            })

        untimed_mins = int(round(untimed_hours * 60))
        total_logged_mins = int(round(total_logged_hours * 60))

        return ok({
            "date": log_date,
            "owner_email": email,
            "projects_with_logs": len(project_names),
            "office_hours": f"{fmt_12h(office_start)} - {fmt_12h(office_end)}",
            "total_logged_hours": round(total_logged_mins / 60, 2),
            "has_untimed_logs": untimed_mins > 0,
            "untimed_hours": round(untimed_mins / 60, 2),
            "free_slots": free_slots,
            "logs": logs,
        })
