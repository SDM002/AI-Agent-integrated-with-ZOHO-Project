"""Project write operation — update existing project fields via v1 POST."""
from typing import Optional
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, ok, err, normalize_date
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client

# Tool: Update Project
@tool
async def update_project(
    project_name: str,
    description: Optional[str] = None,
    name: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> str:
    """
    Update an existing Zoho project (description, name, dates).
    Use this — NOT create_project — whenever the user says 'add/update/set/change description/name/dates' for an existing project.
    Args:
        project_name: Current name of the project to update (required).
        description: New description text.
        name: New project name (to rename).
        start_date: New start date YYYY-MM-DD.
        end_date: New end date YYYY-MM-DD.
    """
    if not project_name: return err("project_name is required.")
    payload = {}
    if description is not None: payload["description"] = description
    if name: payload["name"] = name.strip()
    if start_date:
        d = normalize_date(start_date)
        if d["success"]: payload["start_date"] = d["value"]
    if end_date:
        d = normalize_date(end_date)
        if d["success"]: payload["end_date"] = d["value"]
    if not payload: return err("Provide at least one field to update (description, name, start_date, end_date).")

    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        proj = p_res["value"]

        # Fetch current project details unconditionally to get previous values
        prev_details = await client.get(f"/projects/{proj['id']}/")
        existing = {}
        if prev_details.get("success"):
            projs = prev_details["value"].get("projects", [])
            existing = projs[0] if projs else {}

        # When only one date is given, fetch the existing one so both are always sent together
        if ("end_date" in payload) != ("start_date" in payload):
            if "end_date" in payload and not payload.get("start_date") and existing.get("start_date"):
                payload["start_date"] = existing["start_date"]
            elif "start_date" in payload and not payload.get("end_date") and existing.get("end_date"):
                payload["end_date"] = existing["end_date"]

        res = await client.post_form(f"/projects/{proj['id']}/", data=payload)
        if not res["success"]: return err(res["user_message"])
        
        changes = []
        for key, new_val in payload.items():
            old_val = existing.get(key, "Unknown")
            # Convert date formats if needed, or just leave as is
            changes.append({"field": key.replace("_", " ").title(), "previous_value": old_val, "new_value": new_val})
            
        return ok({
            "updated": True, 
            "project": proj["name"],
            "changes": changes,
            "message": f"Project '{proj['name']}' updated."
        })
