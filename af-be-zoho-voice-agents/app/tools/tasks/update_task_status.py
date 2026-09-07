"""Update task status with Zoho layout resolution and alias mapping."""
import re
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, resolve_task, ok, err
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client

# Per-portal cache of Zoho task status layouts â€” avoids repeated /tasklayouts API calls
TASKLAYOUT_CACHE = {}

# Tool: Update task status (supports aliases + Zoho status ID resolution via tasklayouts)
@tool
async def update_task_status(project_name: str, task_name: str, status: str) -> str:
    """Update task status. Args: project_name, task_name, status (Open|In Progress|Completed|On Hold)."""
    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        t_res = await resolve_task(client, p_res["value"]["id"], task_name)
        if not t_res["success"]: return err(t_res["user_message"])
        proj = p_res["value"]
        task = t_res["value"]
        pid = proj["id"]
        tid = task["id"]

        STATUS_ALIASES = {
            "open":          ["open", "reopen", "re-open", "not started", "new", "todo", "to do"],
            "in progress":   ["in progress", "in-progress", "inprogress", "ongoing", "started", "working", "active", "in_progress", "begin", "start"],
            "in review":     ["in review", "in-review", "inreview", "review", "reviewing", "under review"],
            "to be tested":  ["to be tested", "testing", "test", "needs testing", "qa", "to test", "tobe tested"],
            "on hold":       ["on hold", "on-hold", "onhold", "hold", "paused", "blocked", "pause"],
            "delayed":       ["delayed", "delay", "postponed", "behind schedule", "late"],
            "closed":        ["closed", "close", "completed", "complete", "done", "finish", "finished", "mark complete", "mark done", "end"],
            "cancelled":     ["cancelled", "canceled", "cancel", "abort", "aborted", "dropped", "discard"],
        }

        s = status.lower().strip()
        canonical = next(
            (name for name, aliases in STATUS_ALIASES.items()
             if s in aliases or any(a in s for a in aliases)),
            s,
        )
        status_name = canonical.title()

        def key(x: str) -> str:
            return re.sub(r"[^a-z0-9]+", "", (x or "").lower().strip())

        exact_name_map = {}
        async def collect_status_ids(needkey: str):
            cached = {}
            if pid in TASKLAYOUT_CACHE and TASKLAYOUT_CACHE[pid]:
                for st in TASKLAYOUT_CACHE[pid]:
                    raw_name = str(st.get("name", "")).strip()
                    sid = str(st.get("id", "")).strip()
                    if raw_name and sid:
                        k = key(raw_name)
                        cached[k] = sid
                        exact_name_map[k] = raw_name
                if cached.get(needkey):
                    return cached

            ids = {}
            def add_status(name, sid):
                k = key(name)
                if k and sid and k not in ids:
                    ids[k] = str(sid)
                    exact_name_map[k] = name

            def walk(obj):
                if isinstance(obj, dict):
                    for skey in ("task_statuses", "statuses", "status_list", "custom_statuses", "status_details"):
                        v = obj.get(skey)
                        if isinstance(v, list):
                            for st in v:
                                if isinstance(st, dict) and st.get("id") and (st.get("name") or st.get("display_value")):
                                    add_status(str(st.get("name") or st.get("display_value")), str(st["id"]))
                    fn = str(obj.get("field_name") or obj.get("api_name") or "").lower().strip()
                    if fn in ("status", "task_status", "custom_status"):
                        for optkey in ("values", "pick_list_values", "picklist_values", "options", "allowed_values"):
                            vv = obj.get(optkey)
                            if isinstance(vv, list):
                                for st in vv:
                                    if isinstance(st, dict) and st.get("id") and (st.get("name") or st.get("display_value")):
                                        add_status(str(st.get("name") or st.get("display_value")), str(st["id"]))
                    for v in obj.values(): walk(v)
                elif isinstance(obj, list):
                    for it in obj: walk(it)

            try:
                lr = await client.get(f"/projects/{pid}/tasklayouts")
                if lr["success"]: walk(lr["value"] or {})
            except Exception: pass

            if needkey not in ids and needkey not in cached:
                try:
                    lr2 = await client.get("/tasklayouts")
                    if lr2["success"]: walk(lr2["value"] or {})
                except Exception: pass

            if needkey not in ids and needkey not in cached:
                try:
                    r = await client.get_v3(f"/projects/{pid}/tasks", params={"range": "200"})
                    if r["success"]:
                        for t in r["value"].get("tasks", []):
                            st = t.get("status", {})
                            if isinstance(st, dict) and st.get("id") and st.get("name"):
                                add_status(str(st["name"]), str(st["id"]))
                except Exception: pass

            if "open" not in ids and "open" not in cached:
                try:
                    r_open = await client.get(f"/projects/{pid}/tasks/", params={"per_page": 10})
                    if r_open["success"]:
                        for t in r_open["value"].get("tasks", []):
                            st = t.get("status", {})
                            if isinstance(st, dict) and st.get("id") and st.get("name"):
                                add_status(str(st["name"]), str(st["id"]))
                except Exception: pass

            merged = {**cached, **ids}
            if merged:
                TASKLAYOUT_CACHE[pid] = [{"name": exact_name_map.get(k, k), "id": v} for k, v in merged.items()]
            return merged

        needkey = key(canonical) or key(status)
        status_ids = await collect_status_ids(needkey)
        target_id = status_ids.get(key(canonical)) or status_ids.get(key(status))

        v3_path = f"/projects/{pid}/tasks/{tid}"
        prev_status = "Unknown"
        try:
            prev_res = await client.get_v3(v3_path)
            if prev_res["success"]:
                p_data = prev_res["value"].get("task") or prev_res["value"]
                if isinstance(p_data.get("status"), dict):
                    prev_status = p_data["status"].get("name") or str(p_data["status"])
                else:
                    prev_status = str(p_data.get("status", ""))
        except Exception:
            pass

        if target_id:
            try:
                r = await client.patch_v3(v3_path, {"status": {"id": target_id}})
                if r["success"]:
                    verify = await client.get_v3(v3_path)
                    if verify["success"]:
                        v_data = verify["value"].get("task") or verify["value"]
                        applied_sid = str(v_data.get("status", {}).get("id", ""))
                        if applied_sid == str(target_id):
                            verified_status_name = v_data.get("status", {}).get("name") if isinstance(v_data.get("status"), dict) else status_name
                            return ok({
                                "updated": True,
                                "task": task["name"],
                                "project": proj["name"],
                                "previous_status": prev_status,
                                "new_status": verified_status_name or status_name
                            })
            except Exception: pass

        exact_api_name = exact_name_map.get(key(canonical)) or exact_name_map.get(key(status))
        name_candidates = []
        for n in [exact_api_name, status_name, canonical, status.strip()]:
            if n and n not in name_candidates: name_candidates.append(n)

        for name in name_candidates:
            try:
                # Zoho v1 sometimes ignores fields it doesn't recognize and still returns 200.
                payload = {"status": name}
                if target_id: payload["custom_status"] = target_id
                res = await client.patch_form(f"/projects/{pid}/tasks/{tid}/", payload)
                if res["success"]:
                    verify_v1 = await client.get(f"/projects/{pid}/tasks/{tid}/")
                    if verify_v1["success"] and verify_v1["value"].get("tasks"):
                        t_verify = verify_v1["value"]["tasks"][0]
                        updated_status = t_verify.get("custom_status") or t_verify.get("status", {}).get("name")
                        if updated_status and key(updated_status) == key(name):
                            return ok({
                                "updated": True,
                                "task": task["name"],
                                "project": proj["name"],
                                "previous_status": prev_status,
                                "new_status": updated_status or status_name
                            })
            except Exception: pass

        return err(f"Could not update status to '{status_name}'. Zoho rejected the update. Available statuses: {list(status_ids.keys())}")
