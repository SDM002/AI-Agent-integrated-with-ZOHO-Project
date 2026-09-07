"""Project write operation create a new project."""
from typing import Optional
from langchain_core.tools import tool
from app.tools.helpers import ok, err, normalize_date_iso
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client

# Tool: Create Project
@tool
async def create_project(name: str, description: Optional[str] = None,
                   start_date: Optional[str] = None, end_date: Optional[str] = None) -> str:
    """Create a new Zoho project. Args: name (required), description, start_date (YYYY-MM-DD), end_date (YYYY-MM-DD)."""
    if not name or not name.strip(): return err("Project name is required.")

    payload = {"name": name.strip(), "project_type": "active"}
    if description: payload["description"] = description
    if start_date:
        d = normalize_date_iso(start_date)
        if d["success"]: payload["start_date"] = d["value"]
    if end_date:
        d = normalize_date_iso(end_date)
        if d["success"]: payload["end_date"] = d["value"]

    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        res = await client.post_v3("/projects", data=payload)
        if not res["success"]: return err(res["user_message"])
        data = res["value"]
        projects = data.get("projects")
        if projects:
            p = projects[0]
            return ok({"created": True, "message": f"Project '{p.get('name', name)}' created.",
                       "id": p.get("id_string", str(p.get("id", ""))), "name": p.get("name")})
        return err(f"Failed to create project: {res}")
