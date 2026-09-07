"""Set or update the due date of a task."""
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, resolve_task, normalize_date, ok, err
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client

# Tool: Set or update task due date
@tool
async def set_task_due_date(project_name: str, task_name: str, due_date: str) -> str:
    """Set task due date. Args: project_name, task_name, due_date (YYYY-MM-DD or 'today'/'tomorrow')."""
    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        t_res = await resolve_task(client, p_res["value"]["id"], task_name)
        if not t_res["success"]: return err(t_res["user_message"])
        proj = p_res["value"]
        task = t_res["value"]
        d_res = normalize_date(due_date)
        if not d_res["success"]: return err(d_res["user_message"])

        patch_data = {"end_date": d_res["value"]}
        prev_due_date = "None"
        task_detail = await client.get(f"/projects/{proj['id']}/tasks/{task['id']}/")
        if task_detail["success"] and task_detail["value"].get("tasks"):
            t_raw = task_detail["value"]["tasks"][0]
            prev_due_date = t_raw.get("end_date") or "None"
            existing_start = t_raw.get("start_date", "")
            if existing_start:
                patch_data["start_date"] = existing_start
            else:
                patch_data["start_date"] = d_res["value"]

        res = await client.patch_form(f"/projects/{proj['id']}/tasks/{task['id']}/", data=patch_data)
        if not res["success"]: return err(res["user_message"])
        return ok({
            "updated": True,
            "task": task["name"],
            "project": proj["name"],
            "previous_due_date": prev_due_date,
            "new_due_date": d_res["value"]
        })
