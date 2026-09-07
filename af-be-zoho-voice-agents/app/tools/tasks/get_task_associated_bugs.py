"""Task read operation — list all bugs/issues associated to a task (v3 API)."""
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, resolve_task, ok, err
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client


# Tool: Get Task Associated Bugs
@tool
async def get_task_associated_bugs(project_name: str, task_name: str) -> str:
    """
    List all bugs/issues associated to a specific task in a Zoho project (v3 API).
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

        res = await client.get_v3(f"/projects/{proj['id']}/tasks/{task_id}/associated-bugs")
        if not res["success"]: return err(res["user_message"])

        raw_bugs = res["value"].get("associated_bugs") or res["value"].get("bugs") or res["value"].get("issues") or []
        if not raw_bugs:
            return ok({"task_name": task["name"], "project": proj["name"], "bugs": [],
                       "message": f"No associated bugs on '{task['name']}'."})

        bugs_list = []
        for item in raw_bugs:
            b = item.get("issue") if isinstance(item, dict) and "issue" in item else item
            if not isinstance(b, dict):
                continue
            bug_id = str(b.get("id") or b.get("id_string") or "")
            title  = b.get("name") or b.get("title") or ""
            status = b.get("status_name") or ((b.get("status") or {}).get("name") if isinstance(b.get("status"), dict) else str(b.get("status") or ""))
            severity = b.get("severity_name") or ((b.get("severity") or {}).get("name") if isinstance(b.get("severity"), dict) else str(b.get("severity") or ""))

            # /associated-bugs returns minimal data; fetch full details to get severity
            if not severity and bug_id:
                detail_res = await client.get_v3(f"/projects/{proj['id']}/issues/{bug_id}")
                if detail_res["success"]:
                    raw_detail = detail_res["value"]
                    if isinstance(raw_detail, list):
                        iss = raw_detail[0] if raw_detail else {}
                    else:
                        iss = raw_detail.get("issue") or (raw_detail.get("issues") or [{}])[0] or {}
                    sev_raw = iss.get("severity") or {}
                    severity = (sev_raw.get("value") or sev_raw.get("name", "") if isinstance(sev_raw, dict) else str(sev_raw))

            bugs_list.append({
                "bug_id":   bug_id,
                "title":    title,
                "status":   status,
                "severity": severity,
            })

        return ok({
            "task_name": task["name"],
            "project":   proj["name"],
            "count":     len(bugs_list),
            "bugs":      bugs_list,
        })
