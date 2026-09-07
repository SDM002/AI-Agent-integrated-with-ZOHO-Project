"""Project read operation list all active projects."""
from langchain_core.tools import tool
from app.tools.helpers import ok, err
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client

# Tool: List Active Projects
@tool
async def list_active_projects() -> str:
    """List all active Zoho projects. Call this before any project action."""
    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        res = await client.get("/projects/", params={"status": "active"})
        if not res["success"]: return err(res["user_message"])
        projects = res["value"].get("projects", [])
        if not projects: return ok({"message": "No active projects found."})
        return ok([{"id": p.get("id_string", p.get("id")), "name": p.get("name"),
                    "status": p.get("status")} for p in projects])
