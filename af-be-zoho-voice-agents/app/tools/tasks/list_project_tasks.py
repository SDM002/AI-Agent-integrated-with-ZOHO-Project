"""List tasks in a Zoho project with flexible filtering by status, date range, and owner."""
from datetime import datetime
from typing import Optional
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, resolve_user_by_email, normalize_date, task_status, task_owners, ok, err
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client

# Tool: List tasks in a Zoho project with filters (status, date, owner)
@tool
async def list_project_tasks(
    project_name: str,
    status: Optional[str] = None,
    created_date: Optional[str] = None,
    created_after: Optional[str] = None,
    created_before: Optional[str] = None,
    owner_email: Optional[str] = None,
) -> str:
    """
    List tasks in a project. Supports flexible date filtering.
    Args:
        project_name:   Project name (required).
        status:         Open | In Progress | Completed | On Hold (optional).
        created_date:   Exact day â€” 'today', 'yesterday', 'YYYY-MM-DD'.
        created_after:  Start of date range â€” 'YYYY-MM-DD' (inclusive).
        created_before: End of date range â€” 'YYYY-MM-DD' (inclusive).
        owner_email:    Filter to tasks owned by this email. If the user says 'me' or implies themselves, use the current user's email from context.
    """
    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        proj = p_res["value"]

        res = await client.get(f"/projects/{proj['id']}/tasks/",
                               params={"per_page": 100, "index": 0, "range": 100,
                                       "sort_column": "created_time", "sort_order": "descending"})
        if not res["success"]: return err(res["user_message"])
        tasks = res["value"].get("tasks", [])
        if not tasks: return ok({"message": f"No tasks in '{proj['name']}'."})

        if status:
            sm = {"open": "open", "in progress": "inprogress", "inprogress": "inprogress",
                  "completed": "closed", "closed": "closed", "on hold": "onhold", "onhold": "onhold"}
            tgt = sm.get(status.lower().strip(), status.lower().strip())
            tasks = [t for t in tasks if task_status(t).lower().replace(" ", "") == tgt]

        if owner_email:
            tasks = [t for t in tasks if owner_email.lower() in
                     ", ".join(o.get("email", "") for o in
                               (t.get("details") or {}).get("owners", [])).lower()]

        def to_date(s: str) -> Optional[datetime]:
            d_res = normalize_date(s)
            if d_res["success"]:
                return datetime.strptime(d_res["value"], "%m-%d-%Y")
            return None

        if created_date:
            exact = to_date(created_date)
            if exact:
                tasks = [t for t in tasks if datetime.fromtimestamp(int(t.get("created_time_long", 0)) / 1000).date() == exact.date()]
        elif created_after or created_before:
            after  = to_date(created_after)
            before = to_date(created_before) or datetime.now()
            if after:
                tasks = [t for t in tasks if (d := datetime.fromtimestamp(int(t.get("created_time_long", 0)) / 1000)) and after <= d <= before]

        return ok({
            "project": proj["name"], "count": len(tasks),
            "tasks": [{"id": t.get("id_string"), "name": t.get("name"),
                       "status": task_status(t), "priority": t.get("priority", ""),
                       "owner": task_owners(t), "due_date": t.get("end_date", ""),
                       "created_date": datetime.fromtimestamp(int(t.get("created_time_long", 0)) / 1000).strftime("%Y-%m-%d") if t.get("created_time_long") else ""}
                      for t in tasks]
        })
