"""Response formatters and Zoho task field extractors — standardise tool return values and extract task metadata."""
import json
from typing import Dict

# Serialise any data to a JSON string (used as the standard tool return format)
def ok(data) -> str:
    return json.dumps(data, indent=2, default=str)

# Wrap an error message in the standard tool return format
def err(msg: str) -> str:
    return ok({"error": msg})

# Extract the status name string from a raw Zoho task dict
def task_status(t: Dict) -> str:
    s = t.get("status", {})
    return s.get("name", "") if isinstance(s, dict) else str(s)

# Extract comma-separated owner names from a raw Zoho task dict
def task_owners(t: Dict) -> str:
    return ", ".join(o.get("name", "") for o in
                     (t.get("details") or {}).get("owners", []) if o.get("name"))

# Format a UTC ISO datetime string or epoch timestamp into user's local time (IST, UTC+5:30)
def local_time(val) -> str:
    if not val:
        return ""
    try:
        from datetime import datetime, timezone, timedelta
        from dateutil import parser
        local_tz = timezone.utc
        
        if isinstance(val, (int, float)) or (isinstance(val, str) and val.isdigit()):
            ts = float(val)
            if ts > 1e11:
                ts /= 1000.0
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            local_dt = dt.astimezone(local_tz)
            return local_dt.strftime("%Y-%m-%d %I:%M:%S%p").lower()
            
        utc_iso_str = str(val)
        dt = parser.parse(utc_iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        local_dt = dt.astimezone(local_tz)
        return local_dt.strftime("%Y-%m-%d %I:%M:%S%p").lower()
    except Exception:
        return str(val)
