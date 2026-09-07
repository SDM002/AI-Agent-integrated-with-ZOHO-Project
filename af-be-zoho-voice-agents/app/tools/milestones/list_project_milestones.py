"""Milestone read operations — list all milestones/phases in a project (V3 API)."""
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, ok, err
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client


# Tool: List Project Milestones
@tool
async def list_project_milestones(project_name: str) -> str:
    """List milestones/phases in a project. Args: project_name."""
    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        proj = p_res["value"]

        res = await client.get_v3(f"/projects/{proj['id']}/milestones")
        if not res["success"]: return err(res["user_message"])

        ms = res["value"].get("milestones", [])
        if not ms:
            return ok({"project": proj["name"], "milestones": [],
                       "message": f"No milestones found in '{proj['name']}'."})

        return ok({
            "project":    proj["name"],
            "count":      len(ms),
            "milestones": [
                {
                    "id":        str(m.get("id") or ""),
                    "name":      m.get("name") or "",
                    "status":    m.get("status") or "",
                    "completed": m.get("completed") or False,
                    "due_date":  m.get("end_date") or m.get("due_date") or m.get("end") or "",
                    "owner":     (m.get("owner") or {}).get("name") or m.get("owner_name") or "",
                }
                for m in ms
            ],
        })

