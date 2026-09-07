"""Bug read operation — list all issues linked to a specific issue (v3 API)."""
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, ok, err, resolve_issue
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client


# Tool: Get Linked Bugs
@tool
async def get_linked_bugs(project_name: str, bug_title: str) -> str:
    """
    List all issues linked to a specific issue in a Zoho project (v3 API).
    Args:
        project_name: Project name (required).
        bug_title: Title of the issue (required).
    """
    if not bug_title: return err("bug_title is required.")

    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        proj = p_res["value"]

        src_id, src_title, src_err = await resolve_issue(client, proj["id"], bug_title)
        if src_err: return err(src_err)

        res = await client.get_v3(f"/projects/{proj['id']}/issues/{src_id}/linkedissues")
        if not res["success"]: return err(res["user_message"])

        raw = res["value"]
        issue_linked = raw.get("issue_linked") or []

        # issue_linked is a dict:
        #   {
        #     "linked_issues_count": 1,
        #     "linked_issues": {"is related to": ["436...", ...], ...},
        #     "reverse_linked_issues": {"blocks": ["436...", ...], ...}
        #   }
        # or a plain list of id strings / dicts
        if isinstance(issue_linked, dict):
            link_items = []
            for bucket in ("linked_issues", "reverse_linked_issues"):
                bucket_val = issue_linked.get(bucket) or {}
                if not isinstance(bucket_val, dict):
                    continue
                for link_type, ids in bucket_val.items():
                    if isinstance(ids, list):
                        for x in ids:
                            link_items.append((link_type, x))
                    elif ids:
                        link_items.append((link_type, str(ids)))
        else:
            link_items = [("", x) for x in issue_linked]

        if not link_items:
            return ok({"issue_title": src_title, "project": proj["name"], "links": [],
                       "message": "No linked issues found."})

        import asyncio

        async def resolve_linked(link_type_hint, lk):
            if isinstance(lk, str):
                linked_id = lk
                link_type = link_type_hint
                link_id = ""
                name = ""
            else:
                linked_id = str(lk.get("issue_id") or lk.get("bug_id") or lk.get("id", ""))
                link_type = lk.get("link_type") or lk.get("link_type_name") or link_type_hint
                link_id   = str(lk.get("id") or lk.get("link_id", ""))
                name = lk.get("name") or lk.get("title") or lk.get("issue_name") or lk.get("issue_subject", "")

            # Verify issue still exists (to filter out deleted/broken links)
            detail = await client.get_v3(f"/projects/{proj['id']}/issues/{linked_id}")
            if not detail["success"]:
                return None

            d = detail["value"]
            if isinstance(d, list):
                if not d:
                    return None
                iss = d[0]
            elif isinstance(d, dict):
                iss = d if d.get("name") else (d.get("issue") or (d.get("issues") or [{}])[0] or {})
                if not iss or not iss.get("name"):
                    return None
            else:
                return None

            resolved_name = iss.get("name") or iss.get("title") or "Unknown"
            return {"link_id": link_id, "link_type": link_type,
                    "linked_issue_id": linked_id, "linked_issue_name": resolved_name}

        resolved = await asyncio.gather(*[resolve_linked(t, lk) for t, lk in link_items])
        resolved_filtered = [r for r in resolved if r is not None]

        return ok({
            "issue_title": src_title,
            "project":     proj["name"],
            "count":       len(resolved_filtered),
            "links":       resolved_filtered,
        })

