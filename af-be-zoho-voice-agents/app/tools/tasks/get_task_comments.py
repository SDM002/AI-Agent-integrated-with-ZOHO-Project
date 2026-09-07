"""Task read operation — list all comments on a task (v3 API)."""
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, resolve_task, local_time, ok, err
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client


# Tool: Get Task Comments
@tool
async def get_task_comments(project_name: str, task_name: str) -> str:
    """
    List all comments on a specific task in a Zoho project (v3 API).
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
            f"/projects/{proj['id']}/tasks/{task_id}/comments",
            params={"page": 1, "per_page": 50, "sort_by": "ASC(last_modified_time)"},
        )
        if not res["success"]: return err(res["user_message"])

        comments = res["value"].get("comments") or []
        if not comments:
            return ok({"task_name": task["name"], "project": proj["name"], "comments": [],
                       "message": f"No comments on '{task['name']}'."})

        return ok({
            "task_name": task["name"],
            "project":   proj["name"],
            "count":     len(comments),
            "comments": [
                {
                    "comment_id": str(c.get("id", "")),
                    "comment":    c.get("comment") or c.get("content", ""),
                    "author":     (c.get("author") or c.get("created_by") or {}).get("name", "") if isinstance(c.get("author") or c.get("created_by"), dict) else str(c.get("author", "")),
                    "time":       local_time(c.get("created_time") or c.get("time", "")),
                }
                for c in comments
            ],
        })
