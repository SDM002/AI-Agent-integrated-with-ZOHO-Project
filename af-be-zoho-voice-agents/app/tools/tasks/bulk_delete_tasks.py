"""Bulk delete multiple tasks by name (resolves to numeric IDs internally)."""
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, resolve_task, ok, err
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client

# Tool: Bulk delete tasks
@tool
async def bulk_delete_tasks(project_name: str, task_names: list[str]) -> str:
    """
    Delete multiple tasks by name. Resolves each name to its Zoho ID internally.
    ALWAYS confirm with user before calling. Args: project_name, task_names.
    """
    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        proj = p_res["value"]

        if not task_names: return err("No task names provided.")
        deleted, failed, seen = [], [], set()

        for tname in task_names:
            t_res = await resolve_task(client, proj["id"], tname)
            if not t_res["success"]:
                failed.append({"name": tname, "reason": t_res["user_message"]})
                continue
            task = t_res["value"]
            tid = task["id"]
            if tid in seen:
                continue
            seen.add(tid)
            res = await client.delete(f"/projects/{proj['id']}/tasks/{tid}/")
            if res["success"]:
                deleted.append(task["name"])
            else:
                failed.append({"name": task["name"], "reason": res.get("user_message", "delete failed")})

        return ok({
            "deleted_count": len(deleted),
            "failed_count":  len(failed),
            "deleted":  deleted,
            "failed":   failed,
            "message":  f"Deleted {len(deleted)} task(s) from '{proj['name']}'." +
                        (f" Failed: {', '.join(f['name'] for f in failed)}" if failed else ""),
        })
