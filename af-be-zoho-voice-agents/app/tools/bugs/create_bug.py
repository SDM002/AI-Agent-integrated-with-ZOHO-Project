"""Bug write operations — create a new bug/issue using the v3 API with duplicate detection."""
from typing import Optional
from langchain_core.tools import tool
from app.tools.helpers import (
    resolve_project, resolve_user_by_name, ok, err,
    normalize, score, resolve_field_id, resolve_issue,
)
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client


# Tool: Create Bug
@tool
async def create_bug(
    project_name: str,
    title: str,
    description: Optional[str] = None,
    severity: Optional[str] = None,
    assignee_name: Optional[str] = None,
    flag: Optional[str] = None,
    ignore_duplicate: bool = False,
) -> str:
    """
    Create a bug/issue in a Zoho project (v3 API).
    Checks for duplicate titles before creating.
    Args:
        project_name: Project name (required).
        title: Bug/issue title (required).
        description: Optional description of the bug.
        severity: Minor | Major | Critical | Blocker (optional).
        assignee_name: Display name of the user to assign to (optional). If the user says 'me' or implies themselves, use the current user's email from context.
        flag: 'internal' or 'external' (default: external).
        ignore_duplicate: If True, bypasses duplicate check and creates the bug anyway.
    """
    if not title: return err("title is required.")

    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        proj = p_res["value"]

        # Duplicate title detection — check existing issues before creating
        if not ignore_duplicate:
            existing_id, existing_title, _ = await resolve_issue(client, proj["id"], title, min_score=95)
            if existing_id:
                return ok({
                    "duplicate_found":   True,
                    "existing_issue_id": existing_id,
                    "existing_title":    existing_title,
                    "project":           proj["name"],
                    "message": (
                        f"An issue named '{existing_title}' already exists in '{proj['name']}'. "
                        "Would you like to update it instead, or use a different title?"
                    ),
                })


        # Build v3 JSON payload — field names match curl exactly
        payload: dict = {"name": title}
        if flag:
            payload["flag"] = flag
        if description:
            payload["description"] = description

        # Severity: resolve name → {id} object
        if severity:
            sev_id = await resolve_field_id(client, proj["id"], "severity", severity)
            if sev_id:
                payload["severity"] = {"id": sev_id}

        # Assignee: resolve name → {zpuid} object
        if assignee_name:
            if "@" in assignee_name:
                from app.services.resolvers import resolve_user_by_email
                u_res = await resolve_user_by_email(client, assignee_name, proj["id"])
            else:
                u_res = await resolve_user_by_name(client, assignee_name, proj["id"])
                
            if u_res["success"]:
                payload["assignee"] = {"zpuid": u_res["value"].get("zpuid", "")}
            else:
                return err(f"Failed to assign bug: {u_res['user_message']}")

        res = await client.post_v3(f"/projects/{proj['id']}/issues", data=payload)
        if not res["success"]: return err(res["user_message"])

        raw_val = res["value"]
        if isinstance(raw_val, list):
            created = raw_val[0] if raw_val else {}
        elif isinstance(raw_val, dict):
            created = raw_val.get("issue") or raw_val.get("issues") or raw_val.get("bugs") or raw_val
            if isinstance(created, list):
                created = created[0] if created else {}
        else:
            created = {}
            
        reporter_raw = created.get("reporter") or created.get("created_by") or {}
        reporter_name = reporter_raw.get("name") or reporter_raw.get("display_name") if isinstance(reporter_raw, dict) else str(reporter_raw)

        return ok({
            "created":  True,
            "issue_id": str(created.get("id", "")),
            "title":    title,
            "project":  proj["name"],
            "severity": severity or "default",
            "assignee": assignee_name or "Unassigned",
            "reporter": reporter_name or "Satyadeep Mohanta",
            "message":  f"Issue '{title}' created in '{proj['name']}'.",
        })
