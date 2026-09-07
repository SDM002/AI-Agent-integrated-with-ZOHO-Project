"""Bug write operation — associate tasks to an issue (v3 API)."""
import json
from typing import List
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, resolve_task, ok, err, resolve_issue
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client


# Tool: Associate Tasks to Bug
@tool
async def associate_tasks_to_bug(
    project_name: str,
    bug_title: str,
    task_names: List[str],
) -> str:
    """
    Associate one or more tasks to an issue in a Zoho project (v3 API).
    Args:
        project_name: Project name (required).
        bug_title: Title of the issue (required).
        task_names: List of task names to associate (required).
    """
    if not bug_title:  return err("bug_title is required.")
    if not task_names: return err("task_names must contain at least one task name.")

    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        proj = p_res["value"]

        issue_id, found_title, issue_err = await resolve_issue(client, proj["id"], bug_title)
        if issue_err: return err(issue_err)

        task_ids = []
        for tn in task_names:
            t_res = await resolve_task(client, proj["id"], tn, min_score=80)
            if not t_res["success"]: return err(f"Task '{tn}' not found: {t_res['user_message']}")
            task_ids.append(str(t_res["value"].get("id_string") or t_res["value"].get("id", "")))

        res = await client.post_form_v3(
            f"/projects/{proj['id']}/issues/{issue_id}/associate-tasks",
            data={"task_ids": json.dumps(task_ids)},
        )
        if not res["success"]: return err(res["user_message"])

        return ok({
            "associated":  True,
            "issue_title": found_title,
            "project":     proj["name"],
            "tasks":       task_names,
            "message":     f"{len(task_ids)} task(s) associated to issue '{found_title}'.",
        })
