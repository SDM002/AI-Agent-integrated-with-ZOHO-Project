"""Utility tool — return current date and time in multiple formats."""
from datetime import datetime
from langchain_core.tools import tool
from app.tools.helpers import ok

# Tool: Get Current DateTime
@tool
def get_current_datetime() -> str:
    """Return current date and time. Use for relative date questions like 'today', 'tomorrow'."""
    now = datetime.now()
    return ok({"date": now.strftime("%Y-%m-%d"), "day": now.strftime("%A"),
               "time_12h": now.strftime("%I:%M %p"), "time_24h": now.strftime("%H:%M")})
