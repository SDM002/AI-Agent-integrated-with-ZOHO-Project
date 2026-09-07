"""Create a task in a Zoho project with optional assignment, dates, parent task, and tasklist placement."""
import asyncio
from typing import Optional
from langchain_core.tools import tool
from app.tools.helpers import (
    resolve_project, resolve_task, resolve_tasklist,
    resolve_user_by_name, resolve_user_by_email,
    normalize_date, normalize, ok, err,
)
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client

# Tool: Create a task inside a Zoho project with optional assignment and dates
@tool
async def create_task_on_project(
    project_name: str,
    task_name: str,
    description: Optional[str] = None,
    priority: Optional[str] = "medium",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    owner_name: Optional[str] = None,
    parent_task_name: Optional[str] = None,
    tasklist_name: Optional[str] = None,
) -> str:
    """
    Create a new task in a Zoho project.
    Args:
        project_name, task_name (required), description, priority,
        start_date, end_date, parent_task_name, tasklist_name.
        owner_name: Name or email of the user to assign. If the user says 'me' or implies themselves, use the current user's email from context.
    """
    if not project_name: return err("project_name is required.")
    if not task_name:    return err("task_name is required.")

    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        proj = p_res["value"]
        project_id = proj["id"]

        # Block task names that exactly match the project name (case-insensitive, ignoring punctuation)
        if normalize(task_name) == normalize(proj["name"]):
            return ok({
                "created": False,
                "duplicate_name": True,
                "message": (
                    f"The task name '{task_name}' is the same as the project name '{proj['name']}'. "
                    f"Task names must be different from the project name. "
                    f"Please choose a different task name."
                ),
            })

        existing = await resolve_task(client, project_id, task_name, min_score=100)
        if existing["success"]:
            e = existing["value"]
            # Same name folder check (WebKit logic)
            if tasklist_name:
                tl_res = await resolve_tasklist(client, project_id, tasklist_name)
                if tl_res["success"]:
                    tl_id = str(tl_res["value"]["id"])
                    tasks_res = await client.get(f"/projects/{project_id}/tasklists/{tl_id}/tasks/")
                    if tasks_res["success"]:
                        tl_task_ids = {str(t.get("id_string") or t.get("id", "")) for t in tasks_res["value"].get("tasks", [])}
                        if str(e["id"]) not in tl_task_ids:
                            existing = {"success": False}  # Same name but different folder â†’ allow
            if existing["success"]:
                return ok({"created": False, "message": f"Task '{e['name']}' already exists.", "task_id": e["id"]})

        payload = {"name": task_name, "priority": (priority or "Medium").title()}
        if description: payload["description"] = description
        if end_date:
            d = normalize_date(end_date)
            if d["success"]: payload["end_date"] = d["value"]
        if start_date:
            d = normalize_date(start_date)
            if d["success"]: payload["start_date"] = d["value"]
        if parent_task_name:
            pt = await resolve_task(client, project_id, parent_task_name)
            if pt["success"]: payload["parent_task_id"] = str(pt["value"]["id"])
        if tasklist_name:
            tl_res = await resolve_tasklist(client, project_id, tasklist_name)
            if tl_res["success"]: payload["tasklist_id"] = str(tl_res["value"]["id"])

        assignment_warning = None
        if owner_name:
            u = await resolve_user_by_name(client, owner_name, project_id)
            if u.get("ambiguous"):
                return ok({"ambiguous": True, "candidates": u["candidates"], "message": u["user_message"]})
            if not u["success"]: u = await resolve_user_by_email(client, owner_name, project_id=project_id)
            if u["success"]: payload["person_responsible"] = u["value"]["zpuid"]
            else: assignment_warning = f"Could not assign to '{owner_name}': not found."

        res = await client.post_form(f"/projects/{project_id}/tasks/", data=payload)

        # Verify creation (WebKit "Verify-after-Error" logic)
        for _ in range(3):
            await asyncio.sleep(1)
            verify = await resolve_task(client, project_id, task_name, min_score=95)
            if verify["success"]:
                t = verify["value"]
                msg = f"Task '{task_name}' created successfully in '{proj['name']}'."
                if assignment_warning: msg += f" Warning: {assignment_warning}"
                return ok({"created": True, "message": msg, "task_id": t["id"], "name": t["name"]})

        return err(res.get("user_message") or f"Failed to create task: {res}")
