"""Timelog read operation fetch all logs for a project/date."""
import asyncio
from typing import Optional
from datetime import datetime
from langchain_core.tools import tool
from app.config import SETTINGS, logger
from app.tools.helpers import (
    resolve_project, normalize_date, ok, err,
    resolve_user_by_email, parse_hhmm, parse_12h_to_mins, fmt_12h,
    extract_slot_from_notes, get_slots,
)
from app.utils.request_context import get_user_id, get_request_context
from app.services.zoho.client_factory import build_zoho_client


def office_bounds() -> tuple[int, int]:
    """Return (office_start_mins, office_end_mins) from settings."""
    def to_mins(hhmm: str) -> int:
        h, m = hhmm.strip().split(":")
        return int(h) * 60 + int(m)
    return to_mins(SETTINGS.OFFICE_START_TIME), to_mins(SETTINGS.OFFICE_END_TIME)


def hhmm_to_12h(time_str: str) -> str:
    """Convert 24hr 'HH:MM' → Zoho 12h format with 2-digit hour, e.g. '14:30' → '02:30 PM'."""
    try:
        parts = str(time_str).strip().split(":")
        h, m = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
        period = "AM" if h < 12 else "PM"
        display_h = h if 1 <= h <= 12 else (12 if h == 0 else h - 12)
        return f"{display_h:02d}:{m:02d} {period}"
    except Exception:
        return time_str

# Tool: Get Timelogs for Date (checks existing logs and avoids overlap conflicts)
@tool
async def get_timelogs_for_date(
    project_name: str,
    date: Optional[str] = None,
    owner_email: Optional[str] = None,
) -> str:
    """
    Fetch all time logs for a project on a given date to check booked hours, suggest free slots, and prevent slot conflicts.
    ALWAYS call this before create_time_log.
    Args:
        project_name: Project name (required).
        date: Date YYYY-MM-DD or 'today'/'yesterday' (default: today).
        owner_email: Filter logs to this user's email. If the user says 'me' or implies themselves, use the current user's email from context.
    """
    OFFICE_START, OFFICE_END = office_bounds()

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
            if u_res["success"]: owner_zpuid = u_res["value"]["zpuid"]

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
                    if u_res["success"]: owner_zpuid = u_res["value"]["zpuid"]

        # Zoho API /logs/ requires users_list, view_type, date, and component_type
        params = {
            "date": log_date,
            "view_type": "week" if is_week_view else "day",
            "users_list": "all",
            "bill_status": "All"
        }

        types = ["general", "task", "bug"]
        tasks = [
            client.get(f"/projects/{proj['id']}/logs/", params={**params, "component_type": t})
            for t in types
        ]
        results = await asyncio.gather(*tasks)

        timed_intervals = []
        untimed_hours = 0.0
        all_logs = []

        # Merge in cached slots for eventual consistency
        cached_email = owner_email or ""
        for slot in await get_slots(cached_email, log_date):
            s = slot["start_mins"]
            e = slot["end_mins"]
            if s < e:
                timed_intervals.append((s, e, slot.get("task", "cached")))

        for res, log_type in zip(results, types):
            if not res["success"]:
                logger.error(f"Failed to fetch {log_type} logs: {res['user_message']}")
                continue
            
            data = res["value"]
            tl = data.get("timelogs", {})
            
            raw_list = []
            if "date" in tl:
                for date_obj in tl.get("date", []):
                    # We can filter by date_obj.get("date") to be double-safe, but Zoho filters it by query param
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
                # Client-side date filter (avoids buggy /logs/?date= endpoint)
                if not is_week_view:
                    if raw.get("log_date") and raw["log_date"] != log_date:
                        continue
                # Client-side owner filter
                raw_owner_zpuid = raw.get("owner_zpuid") or raw.get("zpuid") or raw.get("added_by", {}).get("zpuid")
                if owner_zpuid and str(raw_owner_zpuid or "") != str(owner_zpuid):
                    continue
                h_str    = raw.get("hours", "0") or raw.get("hours_display", "0")
                s_str    = raw.get("start_time") or raw.get("from_time")
                e_str    = raw.get("end_time")   or raw.get("to_time")
                label    = raw.get("taskname") or raw.get("name") or raw.get("notes") or "General"
                duration = parse_hhmm(h_str)
                s_mins   = parse_12h_to_mins(s_str) if s_str else None
                e_mins   = parse_12h_to_mins(e_str) if e_str else None

                if s_mins is not None and e_mins is not None:
                    if s_mins < e_mins: timed_intervals.append((s_mins, e_mins, label))
                else:
                    slot_from_notes = extract_slot_from_notes(raw.get("notes") or "")
                    if slot_from_notes:
                        sn, en = slot_from_notes
                        if sn < en: timed_intervals.append((sn, en, label))
                    else: untimed_hours += duration

                task_info = raw.get("task", {}) if isinstance(raw.get("task"), dict) else {}
                all_logs.append({
                    "log_id":         str(raw.get("id_string") or raw.get("id", "")),
                    "task_id":        str(task_info.get("id_string") or task_info.get("id") or raw.get("task_id", "")),
                    "task":           label,
                    "hours":          h_str,
                    "start_time":     s_str,
                    "end_time":       e_str,
                    "date":           raw.get("log_date") or log_date,
                    "billing_status": raw.get("billing_status") or raw.get("bill_status", "Billable"),
                })

        timed_intervals.sort(key=lambda x: x[0])
        merged = []
        for s, e, lbl in timed_intervals:
            if merged and s <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], e), merged[-1][2])
            else: merged.append((s, e, lbl))

        free_slots = []
        cursor = OFFICE_START
        for s, e, _ in merged:
            if cursor < s:
                free_slots.append({
                    "start": fmt_12h(cursor),
                    "end": fmt_12h(s),
                    "duration_hours": round((s - cursor) / 60, 2)
                })
            cursor = max(cursor, e)
        if cursor < OFFICE_END:
            free_slots.append({
                "start": fmt_12h(cursor),
                "end": fmt_12h(OFFICE_END),
                "duration_hours": round((OFFICE_END - cursor) / 60, 2)
            })

        total_booked = sum(e - s for s, e, _ in merged) + int(round(untimed_hours * 60))

        return ok({
            "project": proj["name"], "date": log_date,
            "office_hours": f"{fmt_12h(OFFICE_START)} - {fmt_12h(OFFICE_END)}",
            "booked_hours": round(total_booked / 60, 2),
            "has_untimed_logs": untimed_hours > 0, "untimed_hours": round(untimed_hours, 2),
            "free_slots": free_slots, "logs": all_logs,
        })
