"""Bug read operation — list all tasks associated to an issue (v3 API)."""
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, ok, err, resolve_issue
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client


# Tool: Get Tasks Associated to Bug
@tool
async def get_bug_associated_tasks(project_name: str, bug_title: str) -> str:
    """
    List all tasks associated/linked to a specific issue in a Zoho project (v3 API).
    Args:
        project_name: Project name (required).
        bug_title: Title of the issue (required).
    """
    if not bug_title: return err("bug_title is required.")

    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        proj = p_res["value"]

        issue_id, found_title, issue_err = await resolve_issue(client, proj["id"], bug_title)
        if issue_err: return err(issue_err)

        res = await client.get_v3(
            f"/projects/{proj['id']}/issues/{issue_id}/associated-tasks",
        )
        if not res["success"]: return err(res["user_message"])

        raw = res["value"]
        associated = raw.get("associated_tasks")
        tasks = (
            raw.get("task_array")
            or (associated if isinstance(associated, list) else [])
            or []
        )
        if not tasks:
            return ok({"issue_title": found_title, "project": proj["name"], "tasks": [],
                       "message": "No associated tasks found."})

        return ok({
            "issue_title": found_title,
            "project":     proj["name"],
            "count":       len(tasks),
            "tasks": [
                {
                    "task_id":   str(t.get("TID") or t.get("id_string") or t.get("id") or ""),
                    "task_name": t.get("TTITLE") or t.get("name") or "",
                    "status":    t.get("CUSTOM_STATUSNAME") or ((t.get("status") or {}).get("name") if isinstance(t.get("status"), dict) else str(t.get("status") or "")),
                }
                for t in tasks
            ],
        })
