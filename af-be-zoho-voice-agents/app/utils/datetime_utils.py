"""Date and time parsing utilities — convert natural language dates, HH:MM strings, and slot notation to formats expected by Zoho APIs."""
import re
from datetime import datetime, timedelta
from typing import Dict, Optional

from dateutil.parser import parse as dateutil_parse

# Normalize any date string to Zoho format MM-DD-YYYY (required by v1 API)
def normalize_date(date_str: Optional[str]) -> Dict:
    """Convert any date → MM-DD-YYYY (Zoho v1 required format)."""
    FMT = "%m-%d-%Y"
    now = datetime.now()
    if not date_str or date_str.lower() == "today":
        return {"success": True, "value": now.strftime(FMT)}
    if date_str.lower() == "yesterday":
        return {"success": True, "value": (now - timedelta(days=1)).strftime(FMT)}
    if date_str.lower() == "tomorrow":
        return {"success": True, "value": (now + timedelta(days=1)).strftime(FMT)}
    for fmt in ["%Y-%m-%d", "%m-%d-%Y", "%d-%m-%Y", "%m/%d/%Y", "%d/%m/%Y"]:
        try:
            return {"success": True, "value": datetime.strptime(date_str, fmt).strftime(FMT)}
        except ValueError:
            continue
    try:
        return {"success": True, "value": dateutil_parse(date_str, default=now).strftime(FMT)}
    except Exception:
        return {"success": False, "user_message": f"Invalid date '{date_str}'. Use YYYY-MM-DD."}

# Normalize any date string to ISO format YYYY-MM-DD (required by v3 API)
def normalize_date_iso(date_str: Optional[str]) -> Dict:
    """Convert any date → YYYY-MM-DD (Zoho v3 required format)."""
    FMT = "%Y-%m-%d"
    now = datetime.now()
    if not date_str or date_str.lower() == "today":
        return {"success": True, "value": now.strftime(FMT)}
    if date_str.lower() == "yesterday":
        return {"success": True, "value": (now - timedelta(days=1)).strftime(FMT)}
    if date_str.lower() == "tomorrow":
        return {"success": True, "value": (now + timedelta(days=1)).strftime(FMT)}
    for fmt in ["%Y-%m-%d", "%m-%d-%Y", "%d-%m-%Y", "%m/%d/%Y", "%d/%m/%Y"]:
        try:
            return {"success": True, "value": datetime.strptime(date_str, fmt).strftime(FMT)}
        except ValueError:
            continue
    try:
        return {"success": True, "value": dateutil_parse(date_str, default=now).strftime(FMT)}
    except Exception:
        return {"success": False, "user_message": f"Invalid date '{date_str}'. Use YYYY-MM-DD."}

# Parse HH:MM or decimal hours string to a float hour value
def parse_hhmm(hhmm: str) -> float:
    try:
        if ":" in str(hhmm):
            parts = str(hhmm).split(":")
            return int(parts[0]) + int(parts[1]) / 60
        return float(hhmm)
    except Exception:
        return 0.0

# Convert 12-hour time string to total minutes since midnight
def parse_12h_to_mins(time_str: str) -> Optional[int]:
    try:
        parts = str(time_str).strip().upper().split()
        period = parts[1] if len(parts) > 1 else "AM"
        hm = parts[0].split(":")
        h, m = int(hm[0]), int(hm[1]) if len(hm) > 1 else 0
        if period == "PM" and h != 12: h += 12
        elif period == "AM" and h == 12: h = 0
        return h * 60 + m
    except Exception:
        return None

# Format total minutes since midnight to 12-hour display string (e.g. 870 → '2:30 PM')
def fmt_12h(total_minutes: int) -> str:
    h, m = divmod(total_minutes, 60)
    period = "AM" if h < 12 else "PM"
    display_h = h if 1 <= h <= 12 else (12 if h == 0 else h - 12)
    return f"{display_h}:{m:02d} {period}"

# Extract a [HH:MM-HH:MM] time slot embedded in a task notes string
def extract_slot_from_notes(notes: str) -> Optional[tuple]:
    if not notes: return None
    m = re.search(r'\[(\d{2}:\d{2})-(\d{2}:\d{2})\]', notes)
    if not m: return None
    def mn(t: str) -> int:
        p = t.split(":")
        return int(p[0]) * 60 + int(p[1])
    return (mn(m.group(1)), mn(m.group(2)))

# Convert float hours to HH:MM format required by Zoho v1 timelog API
def format_hours(hours: float) -> str:
    minutes = int(round(hours * 60))
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def parse_date_range(date_str: Optional[str]) -> tuple[str, str, bool]:
    """
    Parse a natural language date or date range into (start_date_iso, end_date_iso, is_week_view).
    """
    FMT = "%Y-%m-%d"
    now = datetime.now()
    
    if not date_str:
        today_str = now.strftime(FMT)
        return today_str, today_str, False
        
    date_clean = date_str.lower().strip()
    
    # 1. Handle Week view
    if "week" in date_clean:
        clean_date = (
            date_clean
            .replace("this week", "")
            .replace("week of", "")
            .replace("first week of", "")
            .replace("last week", "")
            .replace("week", "")
            .replace("of", "")
            .replace("first", "")
            .replace("second", "")
            .replace("third", "")
            .replace("fourth", "")
            .strip()
        )
        
        ref_date = now
        if "last" in date_clean:
            ref_date = now - timedelta(days=7)
        elif clean_date:
            try:
                ref_date = dateutil_parse(clean_date, default=datetime(now.year, now.month, 1))
            except Exception:
                pass
                
        start_of_week = ref_date - timedelta(days=ref_date.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        return start_of_week.strftime(FMT), end_of_week.strftime(FMT), True

    # 2. Handle Date Ranges (to, between, and, -)
    if date_clean.startswith("between "):
        date_clean = date_clean[8:]
    if " and " in date_clean:
        date_clean = date_clean.replace(" and ", " to ")
        
    for delim in [" to ", " - ", "-"]:
        if delim in date_clean:
            parts = date_clean.split(delim, 1)
            p1, p2 = parts[0].strip(), parts[1].strip()
            r1 = normalize_date_iso(p1)
            r2 = normalize_date_iso(p2)
            if r1["success"] and r2["success"]:
                v1, v2 = r1["value"], r2["value"]
                if v1 > v2:
                    v1, v2 = v2, v1
                return v1, v2, False

    # 3. Single Date
    r = normalize_date_iso(date_clean)
    if r["success"]:
        return r["value"], r["value"], False
        
    today_str = now.strftime(FMT)
    return today_str, today_str, False

