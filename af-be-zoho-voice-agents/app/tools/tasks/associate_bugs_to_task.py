"""Task write operation — associate bugs/issues to a task (v3 POST API)."""
import json
from typing import List
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, resolve_task, resolve_issue, ok, err
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client


# Tool: Associate Bugs to Task
@tool
async def associate_bugs_to_task(
    project_name: str,
    task_name: str,
    bug_titles: List[str],
) -> str:
    """
    Associate one or more bugs/issues to a task in a Zoho project (v3 POST API).
    Args:
        project_name: Project name (required).
        task_name: Task name (required).
        bug_titles: List of bug/issue titles to associate (required).
    """
    if not task_name:  return err("task_name is required.")
    if not bug_titles: return err("bug_titles must contain at least one title.")

    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        proj = p_res["value"]

        t_res = await resolve_task(client, proj["id"], task_name)
        if not t_res["success"]: return err(t_res["user_message"])
        task = t_res["value"]
        task_id = str(task.get("id_string") or task.get("id", ""))

        bug_ids = []
        for title in bug_titles:
            issue_id, _, issue_err = await resolve_issue(client, proj["id"], title)
            if issue_err: return err(f"Bug '{title}' not found: {issue_err}")
            bug_ids.append(issue_id)

        res = await client.post_form_v3(
            f"/projects/{proj['id']}/tasks/{task_id}/associate-bugs",
            data={"bug_ids": json.dumps(bug_ids)},
        )
        if not res["success"]: return err(res["user_message"])

        return ok({
            "associated": True,
            "task_name":  task["name"],
            "bugs":       bug_titles,
            "project":    proj["name"],
            "message":    f"{len(bug_ids)} bug(s) associated to task '{task['name']}'.",
        })
