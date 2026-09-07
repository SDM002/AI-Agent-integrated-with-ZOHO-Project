"""Bug write operations — update an existing issue via PATCH using the v3 API."""
from typing import Optional
from langchain_core.tools import tool
from app.tools.helpers import (
    resolve_project, resolve_user_by_name, ok, err,
    resolve_issue, resolve_field_id,
)
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client


# Tool: Update Bug
@tool
async def update_bug(
    project_name: str,
    bug_title: str,
    status: Optional[str] = None,
    assignee_name: Optional[str] = None,
    severity: Optional[str] = None,
    new_title: Optional[str] = None,
    description: Optional[str] = None,
) -> str:
    """
    Update an existing bug or issue in a Zoho project.
    Use for any change to a bug/issue: status, assignee, severity, title, or description.
    Use this tool (not update_task_status) whenever the user mentions a bug or issue by name.
    Args:
        project_name: Project name (required).
        bug_title: Title of the bug/issue (required).
        status: New status — Open, In progress, To be tested, Closed.
        assignee_name: Display name of the user to assign. If the user says 'me' or implies themselves, use the current user's email from context.
        severity: Minor | Major | Critical | Blocker.
        new_title: New title to rename the bug.
        description: New description text.
    """
    if not bug_title: return err("bug_title is required to locate the issue.")

    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        proj = p_res["value"]

        issue_id, found_title, issue_err = await resolve_issue(client, proj["id"], bug_title)
        if issue_err: return err(issue_err)

        payload: dict = {}

        if new_title:
            payload["name"] = new_title
        if description:
            payload["description"] = description

        # Severity: resolve name → {id} object via defaultfields
        if severity:
            sev_id = await resolve_field_id(client, proj["id"], "severity", severity)
            if sev_id:
                payload["severity"] = {"id": sev_id}
            else:
                return err(f"Severity '{severity}' not found. Valid: Minor, Major, Critical, Blocker.")

        # Status: try statustransition first (shows allowed next statuses for this issue)
        if status:
            st_res = await client.get_v3(f"/projects/{proj['id']}/issues/{issue_id}/statustransition")
            status_id = None
            if st_res["success"]:
                raw = st_res["value"]
                if isinstance(raw, list):
                    transitions = raw
                else:
                    transitions = (
                        raw.get("status_transitions")
                        or raw.get("statustransitions")
                        or raw.get("transitions")
                        or []
                    )
                from app.utils.string_matching import normalize, score
                st_target = normalize(status)
                best_st, best_sc = None, 0
                for tr in transitions:
                    tr_name = tr.get("name") or tr.get("status_name") or ""
                    s = score(st_target, normalize(tr_name))
                    if s > best_sc:
                        best_sc, best_st = s, tr
                if best_st and best_sc >= 70:
                    status_id = str(best_st.get("id") or best_st.get("status_id") or "")

            # Fallback: resolve from defaultfields
            if not status_id:
                status_id = await resolve_field_id(client, proj["id"], "status", status)

            if status_id:
                payload["status"] = {"id": status_id}
            else:
                return err(f"Status '{status}' not found. Check available statuses in Zoho portal.")

        # Assignee: resolve name → {zpuid} object
        if assignee_name:
            if "@" in assignee_name:
                from app.services.resolvers import resolve_user_by_email
                u_res = await resolve_user_by_email(client, assignee_name, proj["id"])
            else:
                u_res = await resolve_user_by_name(client, assignee_name, proj["id"])
                
            if not u_res["success"]: return err(u_res["user_message"])
            payload["assignee"] = {"zpuid": u_res["value"].get("zpuid", "")}

        if not payload:
            return err("Nothing to update — provide at least one of: status, assignee_name, severity, new_title, description.")

        # Get previous details
        prev_status = "None"
        prev_assignee = "Unassigned"
        prev_severity = "None"
        prev_title = found_title
        prev_description = ""
        try:
            prev_res = await client.get_v3(f"/projects/{proj['id']}/issues/{issue_id}")
            if prev_res["success"]:
                raw_val = prev_res["value"]
                if isinstance(raw_val, list):
                    p_data = raw_val[0] if raw_val else {}
                else:
                    p_data = raw_val.get("issue") or (raw_val.get("issues") or [{}])[0] or {}
                
                prev_status = (p_data.get("status") or {}).get("name") if isinstance(p_data.get("status"), dict) else str(p_data.get("status") or "None")
                prev_severity = (p_data.get("severity") or {}).get("value") or (p_data.get("severity") or {}).get("name") if isinstance(p_data.get("severity"), dict) else str(p_data.get("severity") or "None")
                prev_assignee = (p_data.get("assignee") or {}).get("name") if isinstance(p_data.get("assignee"), dict) else str(p_data.get("assignee") or "Unassigned")
                prev_title = p_data.get("name") or p_data.get("title") or found_title
                prev_description = p_data.get("description") or ""
        except Exception:
            pass

        res = await client.patch_v3(f"/projects/{proj['id']}/issues/{issue_id}", data=payload)
        if not res["success"]: return err(res["user_message"])

        return ok({
            "updated":            True,
            "issue_id":           issue_id,
            "issue_title":        new_title or found_title,
            "project":            proj["name"],
            "previous_status":    prev_status,
            "new_status":         status or prev_status,
            "previous_severity":  prev_severity,
            "new_severity":       severity or prev_severity,
            "previous_assignee":  prev_assignee,
            "new_assignee":       assignee_name or prev_assignee,
            "previous_title":     prev_title,
            "new_title":          new_title or prev_title,
            "previous_description": prev_description,
            "new_description":    description or prev_description
        })
