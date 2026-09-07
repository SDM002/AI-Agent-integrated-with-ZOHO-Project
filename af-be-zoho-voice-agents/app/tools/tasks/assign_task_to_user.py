"""Assign a task to a team member with membership verification."""
from langchain_core.tools import tool
from app.tools.helpers import resolve_project, resolve_task, resolve_user_by_name, resolve_user_by_email, task_owners, ok, err
from app.utils.request_context import get_user_id
from app.services.zoho.client_factory import build_zoho_client

# Tool: Assign task to a user in the project
@tool
async def assign_task_to_user(project_name: str, task_name: str, owner_name: str) -> str:
    """
    Assign a task to a team member. 
    Args: 
        project_name: Name of the project
        task_name: Name of the task
        owner_name: Name or email of the user to assign. If the user says 'assign to me', use the current user's email from context.
    """
    user_id = get_user_id()
    async with await build_zoho_client(user_id) as client:
        p_res = await resolve_project(client, project_name)
        if not p_res["success"]: return err(p_res["user_message"])
        proj = p_res["value"]
        t_res = await resolve_task(client, proj["id"], task_name)
        if not t_res["success"]: return err(t_res["user_message"])
        task = t_res["value"]
        u_res = await resolve_user_by_name(client, owner_name, proj["id"])
        if u_res.get("ambiguous"):
            return ok({"ambiguous": True, "candidates": u_res["candidates"], "message": u_res["user_message"]})
        if not u_res["success"]:
            u_res = await resolve_user_by_email(client, owner_name, project_id=proj["id"])
        if not u_res["success"]: return err(u_res["user_message"])
        user = u_res["value"]

        zpuid = user.get("zpuid", "")
        email = user.get("email", "")

        # Membership check â€” confirm user belongs to the project before assigning
        members_res = await client.get(f"/projects/{proj['id']}/users/")
        if not members_res["success"]: return err(members_res["user_message"])
        project_emails = {(u.get("email") or "").lower() for u in members_res["value"].get("users", [])}
        if email.lower() not in project_emails:
            return ok({
                "not_a_member": True, "user": user["name"], "project": proj["name"],
                "message": f"'{user['name']}' is not a member of '{proj['name']}'. Would you like to add them first?"
            })

        # Fetch current task details to get the previous owner
        task_details_res = await client.get(f"/projects/{proj['id']}/tasks/{task['id']}/")
        prev_owner = "None"
        if task_details_res.get("success") and task_details_res["value"].get("tasks"):
            prev_owner = task_owners(task_details_res["value"]["tasks"][0]) or "None"

        # Multiple fields for assignment
        patch_data = {"person_responsible": zpuid, "person_responsible_zpuid": zpuid, "owners": email}
        await client.patch_form(f"/projects/{proj['id']}/tasks/{task['id']}/", data=patch_data)

        # Verify assignment applied
        check = await client.get(f"/projects/{proj['id']}/tasks/{task['id']}/")
        if check["success"] and check["value"].get("tasks"):
            t_raw = check["value"]["tasks"][0]
            if task_owners(t_raw) or str(t_raw.get("person_responsible", "")) == zpuid:
                return ok({
                    "assigned": True,
                    "task": task["name"],
                    "project": proj["name"],
                    "changes": [
                        {
                            "field": "Assignee",
                            "previous_value": prev_owner,
                            "new_value": user["name"]
                        }
                    ]
                })

        return err(f"Assignment failed for '{user['name']}'. Please assign manually in Zoho.")

