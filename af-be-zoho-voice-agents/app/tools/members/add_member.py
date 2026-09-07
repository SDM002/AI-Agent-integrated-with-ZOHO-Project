"""Member write operations add a user to a project by email."""
from typing import Optional
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, resolve_user_by_email, ok, err
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client

# Tool: Add User to Project
@tool
async def add_user_to_project(project_name: str, user_email: str, role_name: str) -> str:
    """Add a user to a Zoho project. 
    Args: 
        project_name: Project name (required). 
        user_email: Email of user (required). If the user says 'me' or implies themselves, use the current user's email from context.
        role_name: Role to assign. Must be exactly one of: Employee, Administrator, Manager, Contractor. (required, do not guess - if missing, you MUST ask the user).
    """
    if not role_name or str(role_name).strip().lower() in ["none", "null", "unknown", ""]:
        return err("Missing role_name. You MUST ask the user which role to assign (Employee, Administrator, Manager, or Contractor) before proceeding.")

    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        proj = p_res["value"]

        u_res = await resolve_user_by_email(client, user_email)
        if not u_res["success"]: return err(u_res["user_message"])
        user = u_res["value"]

        valid_roles = {"employee", "administrator", "manager", "contractor"}
        clean_role = role_name.lower().strip()
        if clean_role not in valid_roles:
            return err(f"Invalid role '{role_name}'. Valid roles are: Employee, Administrator, Manager, Contractor.")

        res = await client.post_form(
            f"/projects/{proj['id']}/users/",
            data={"email": user["email"], "role": clean_role},
        )
        if not res["success"]: return err(res["user_message"])
        return ok({
            "added": True, 
            "user": user["name"], 
            "project": proj["name"],
            "role": clean_role.title(),
            "message": f"User {user['name']} added to {proj['name']} as {clean_role.title()}."
        })
