"""Bug read operations — get full details, description, and allowed status transitions for a bug/issue (v3 API)."""
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, local_time, ok, err, resolve_issue
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client


# Tool: Get Bug Details
@tool
async def get_bug_details(project_name: str, bug_title: str) -> str:
    """
    Get full details of a specific bug/issue in a Zoho project (v3 API).
    Returns status, severity, assignee, reporter, description, and allowed next statuses.
    Args:
        project_name: Project name (required).
        bug_title: Title of the bug (required — used to locate it).
    """
    if not bug_title: return err("bug_title is required.")

    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        proj = p_res["value"]

        issue_id, found_title, issue_err = await resolve_issue(client, proj["id"], bug_title)
        if issue_err: return err(issue_err)

        # GET /api/v3/.../issues/{issueId}
        detail_res = await client.get_v3(f"/projects/{proj['id']}/issues/{issue_id}")
        if not detail_res["success"]: return err(detail_res["user_message"])

        raw_detail = detail_res["value"]
        if isinstance(raw_detail, list):
            iss = raw_detail[0] if raw_detail else {}
        else:
            iss = (
                raw_detail.get("issue")
                or (raw_detail.get("issues") or [{}])[0]
                or {}
            )

        status_raw   = iss.get("status") or {}
        severity_raw = iss.get("severity") or {}
        assignee_raw = iss.get("assignee") or {}
        reporter_raw = iss.get("reporter") or iss.get("created_by") or {}

        # GET /api/v3/.../issues/{issueId}/description
        description = iss.get("description", "")
        desc_res = await client.get_v3(f"/projects/{proj['id']}/issues/{issue_id}/description")
        if desc_res["success"]:
            desc_data = desc_res["value"]
            description = (
                desc_data.get("description")
                or desc_data.get("content")
                or description
            )

        # GET /api/v3/.../issues/{issueId}/statustransition — shows allowed next statuses
        allowed_statuses = []
        st_res = await client.get_v3(f"/projects/{proj['id']}/issues/{issue_id}/statustransition")
        if st_res["success"]:
            raw_st = st_res["value"]
            if isinstance(raw_st, list):
                transitions = raw_st
            else:
                transitions = (
                    raw_st.get("status_transitions")
                    or raw_st.get("statustransitions")
                    or raw_st.get("transitions")
                    or []
                )
            allowed_statuses = [tr.get("name") or tr.get("status_name", "") for tr in transitions if tr.get("name") or tr.get("status_name")]

        return ok({
            "issue_id":        issue_id,
            "title":           iss.get("name") or iss.get("title", ""),
            "project":         proj["name"],
            "status":          status_raw.get("name", "") if isinstance(status_raw, dict) else str(status_raw),
            "severity":        severity_raw.get("value") or severity_raw.get("name", "") if isinstance(severity_raw, dict) else str(severity_raw),
            "assignee":        assignee_raw.get("name", "") if isinstance(assignee_raw, dict) else str(assignee_raw),
            "reporter":        reporter_raw.get("name", "") if isinstance(reporter_raw, dict) else str(reporter_raw),
            "description":     description,
            "due_date":        iss.get("due_date", ""),
            "created_time":    local_time(iss.get("created_time", "")),
            "flag":            iss.get("flag", ""),
            "allowed_statuses": allowed_statuses,
        })
