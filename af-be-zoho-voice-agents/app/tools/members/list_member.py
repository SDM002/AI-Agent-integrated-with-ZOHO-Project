"""Member read operations list all team members in a project."""
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, ok, err
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client

# Tool: List Project Members
@tool
async def list_project_members(project_name: str) -> str:
    """List all team members in a project. Args: project_name."""
    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        proj = p_res["value"]

        res = await client.get(f"/projects/{proj['id']}/users/")
        if not res["success"]: return err(res["user_message"])
        users = res["value"].get("users", [])
        if not users: return ok({"message": f"No members in '{proj['name']}'."})

        return ok({"project": proj["name"], "count": len(users),
                   "members": [{"name": u.get("name", u.get("full_name", "")),
                                "email": u.get("email", ""), "role": u.get("role", "")}
                               for u in users]})
