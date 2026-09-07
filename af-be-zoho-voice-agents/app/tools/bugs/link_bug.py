"""Bug write operation — link one issue to another (v3 POST API)."""
import json
from typing import Optional
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, ok, err, resolve_issue
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client


# Tool: Link Bugs
@tool
async def link_bugs(
    project_name: str,
    bug_title: str,
    linked_bug_title: str,
    link_type: Optional[str] = "relate",
) -> str:
    """
    Link one issue to another in a Zoho project (v3 API).
    Args:
        project_name: Project name (required).
        bug_title: Title of the source issue (required).
        linked_bug_title: Title of the issue to link to (required).
        link_type: 'relate' (default) | 'duplicate' | 'blocked_by' | 'blocks'.
    """
    if not bug_title:        return err("bug_title is required.")
    if not linked_bug_title: return err("linked_bug_title is required.")

    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        proj = p_res["value"]

        if str(bug_title).isdigit():
            src_id = str(bug_title)
            src_title = f"Bug ID: {src_id}"
        else:
            src_id, src_title, src_err = await resolve_issue(client, proj["id"], bug_title)
            if src_err: return err(src_err)

        if str(linked_bug_title).isdigit():
            tgt_id = str(linked_bug_title)
            tgt_title = f"Bug ID: {tgt_id}"
        else:
            tgt_id, tgt_title, tgt_err = await resolve_issue(client, proj["id"], linked_bug_title)
            if tgt_err: return err(tgt_err)

        res = await client.post_v3(
            f"/projects/{proj['id']}/issues/{src_id}/link",
            data={"link_type": link_type or "relate", "issue_ids": json.dumps([tgt_id])},
        )
        if not res["success"]: return err(res["user_message"])

        return ok({
            "linked":       True,
            "source_issue": src_title,
            "linked_issue": tgt_title,
            "link_type":    link_type or "relate",
            "project":      proj["name"],
            "message":      f"Issue '{src_title}' linked to '{tgt_title}' as '{link_type or 'relate'}'.",
        })
