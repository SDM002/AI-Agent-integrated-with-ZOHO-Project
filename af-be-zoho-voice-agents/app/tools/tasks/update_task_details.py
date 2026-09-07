"""Update multiple task fields (dates + priority) in a single API call."""
from typing import Optional
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, resolve_task, normalize_date, ok, err
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client

# Tool: Update multiple task fields at once (dates + priority in one API call)
@tool
async def update_task_details(project_name: str, task_name: str,
                        start_date: Optional[str] = None,
                        due_date: Optional[str] = None,
                        priority: Optional[str] = None) -> str:
    """Update multiple task fields (dates, priority) in ONE request. Args: project_name, task_name, start_date, due_date, priority."""
    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        t_res = await resolve_task(client, p_res["value"]["id"], task_name)
        if not t_res["success"]: return err(t_res["user_message"])
        proj = p_res["value"]
        task = t_res["value"]

        patch_data = {}
        if priority: patch_data["priority"] = priority.title()
        if start_date:
            d_res = normalize_date(start_date)
            if d_res["success"]: patch_data["start_date"] = d_res["value"]
        if due_date:
            d_res = normalize_date(due_date)
            if d_res["success"]: patch_data["end_date"] = d_res["value"]

        if not patch_data: return err("No updates provided.")

        prev_start_date = "None"
        prev_due_date = "None"
        prev_priority = "None"
        task_detail = await client.get(f"/projects/{proj['id']}/tasks/{task['id']}/")
        if task_detail["success"] and task_detail["value"].get("tasks"):
            t_raw = task_detail["value"]["tasks"][0]
            prev_start_date = t_raw.get("start_date") or "None"
            prev_due_date = t_raw.get("end_date") or "None"
            prev_priority = str(t_raw.get("priority", "none")).title()

            if ("start_date" in patch_data and "end_date" not in patch_data) or \
               ("end_date" in patch_data and "start_date" not in patch_data):
                if "start_date" not in patch_data and t_raw.get("start_date"):
                    patch_data["start_date"] = t_raw["start_date"]
                if "end_date" not in patch_data and t_raw.get("end_date"):
                    patch_data["end_date"] = t_raw["end_date"]

        res = await client.patch_form(f"/projects/{proj['id']}/tasks/{task['id']}/", patch_data)
        if not res["success"]: return err(res["user_message"])
        return ok({
            "updated": True,
            "task": task["name"],
            "project": proj["name"],
            "previous_start_date": prev_start_date,
            "new_start_date": patch_data.get("start_date") or prev_start_date,
            "previous_due_date": prev_due_date,
            "new_due_date": patch_data.get("end_date") or prev_due_date,
            "previous_priority": prev_priority,
            "new_priority": patch_data.get("priority") or prev_priority
        })
