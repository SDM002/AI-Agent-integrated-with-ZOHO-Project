"""Bug write operation — remove a task association from an issue (v3 DELETE API)."""
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, resolve_task, ok, err, resolve_issue
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client


# Tool: Disassociate Task from Bug
@tool
async def disassociate_task_from_bug(
    project_name: str,
    bug_title: str,
    task_name: str,
) -> str:
    """
    Remove the association between a task and an issue in a Zoho project (v3 DELETE API).
    Args:
        project_name: Project name (required).
        bug_title: Title of the issue (required).
        task_name: Name of the task to disassociate (required).
    """
    if not bug_title: return err("bug_title is required.")
    if not task_name: return err("task_name is required.")

    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        proj = p_res["value"]

        issue_id, found_title, issue_err = await resolve_issue(client, proj["id"], bug_title)
        if issue_err: return err(issue_err)

        t_res = await resolve_task(client, proj["id"], task_name, min_score=80)
        if not t_res["success"]: return err(f"Task '{task_name}' not found: {t_res['user_message']}")
        task_id = str(t_res["value"].get("id_string") or t_res["value"].get("id", ""))

        res = await client.delete_v3(f"/projects/{proj['id']}/issues/{issue_id}/task/{task_id}")
        if not res["success"]: return err(res["user_message"])

        return ok({
            "disassociated": True,
            "issue_title":   found_title,
            "task_name":     task_name,
            "project":       proj["name"],
            "message":       f"Task '{task_name}' disassociated from issue '{found_title}'.",
        })
