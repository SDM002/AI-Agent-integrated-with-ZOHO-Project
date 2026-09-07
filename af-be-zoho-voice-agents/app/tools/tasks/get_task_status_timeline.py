"""Task read operation — get the status timeline for a task (v3 API)."""
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, resolve_task, local_time, ok, err
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client


# Tool: Get Task Status Timeline
@tool
async def get_task_status_timeline(project_name: str, task_name: str) -> str:
    """
    Get the status change timeline for a specific task in a Zoho project (v3 API).
    Args:
        project_name: Project name (required).
        task_name: Task name (required).
    """
    if not task_name: return err("task_name is required.")

    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        proj = p_res["value"]

        t_res = await resolve_task(client, proj["id"], task_name)
        if not t_res["success"]: return err(t_res["user_message"])
        task = t_res["value"]
        task_id = str(task.get("id_string") or task.get("id", ""))

        res = await client.get_v3(
            f"/projects/{proj['id']}/tasks/{task_id}/status-timeline",
            params={"page": 1, "per_page": 50},
        )
        if not res["success"]: return err(res["user_message"])

        raw = res["value"]

        # Zoho v3 wraps the list under various keys — try all known variants.
        # Also keep the full raw response available for transparent passthrough.
        if isinstance(raw, list):
            timeline = raw
        elif isinstance(raw, dict):
            timeline = (raw.get("status_timeline") or raw.get("timeline") or
                        raw.get("status_timelines") or [])
        else:
            timeline = []

        if not timeline:
            raw_keys = list(raw.keys()) if isinstance(raw, dict) else []
            # Return the raw Zoho response so the LLM can see all top-level keys
            # and report exactly what came back (helps diagnose wrong key names).
            return ok({
                "task_name": task["name"],
                "project":   proj["name"],
                "timeline":  [],
                "message":   f"No status history entries found for '{task['name']}' using standard keys. However, the API returned the following keys: {raw_keys}. Please tell the user what these keys are so the developer can fix the tool.",
                "raw_response": raw if isinstance(raw, dict) else {},
            })

        def _name(field):
            if isinstance(field, dict):
                return (field.get("name") or field.get("full_name") or
                        field.get("display_name") or field.get("email") or
                        str(field))
            return str(field) if field else ""

        def _entry(e):
            duration_obj = e.get("duration") or {}
            duration_str = duration_obj.get("total_time") or ""
            return {
                "from_status": _name(
                    e.get("previous_status") or e.get("from_status") or e.get("status") or
                    e.get("status_name") or e.get("from") or ""
                ),
                "to_status": _name(
                    e.get("updated_status") or e.get("to_status") or e.get("to") or ""
                ),
                "changed_by": _name(
                    e.get("updated_by") or e.get("changed_by") or
                    e.get("user") or e.get("created_by") or ""
                ),
                "time": local_time(
                    e.get("updated_on") or e.get("changed_time") or e.get("updated_time") or
                    e.get("created_time") or e.get("time") or ""
                ),
                "duration": duration_str,
            }

        entries = [_entry(e) for e in timeline]
        return ok({
            "task_name": task["name"],
            "project":   proj["name"],
            "count":     len(timeline),
            "timeline":  entries,
        })
