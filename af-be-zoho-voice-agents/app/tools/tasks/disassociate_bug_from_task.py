"""Task write operation — remove a bug/issue association from a task (v3 DELETE API)."""
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, resolve_task, resolve_issue, ok, err
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client


# Tool: Disassociate Bug from Task
@tool
async def disassociate_bug_from_task(
    project_name: str,
    task_name: str,
    bug_title: str,
) -> str:
    """
    Remove the association between a bug/issue and a task in a Zoho project (v3 DELETE API).
    Args:
        project_name: Project name (required).
        task_name: Task name (required).
        bug_title: Title of the bug/issue to disassociate (required).
    """
    if not task_name: return err("task_name is required.")
    if not bug_title: return err("bug_title is required.")

    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        proj = p_res["value"]

        t_res = await resolve_task(client, proj["id"], task_name)
        if not t_res["success"]: return err(t_res["user_message"])
        task = t_res["value"]
        task_id = str(task.get("id_string") or task.get("id", ""))

        issue_id, found_title, issue_err = await resolve_issue(client, proj["id"], bug_title)
        if issue_err: return err(issue_err)

        res = await client.delete_v3(f"/projects/{proj['id']}/tasks/{task_id}/bug/{issue_id}")
        if not res["success"]: return err(res["user_message"])

        return ok({
            "disassociated": True,
            "task_name":     task["name"],
            "bug_title":     found_title,
            "project":       proj["name"],
            "message":       f"Bug '{found_title}' disassociated from task '{task['name']}'.",
        })
