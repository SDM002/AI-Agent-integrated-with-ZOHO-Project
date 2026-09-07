"""
Tool registry — aggregates and exposes all Zoho agent tools.
"""
from app.tools.projects import list_active_projects, get_project_details, create_project, update_project
from app.tools.tasks import (
    list_project_tasks, create_task_on_project, update_task_status,
    assign_task_to_user, update_task_priority, set_task_due_date,
    add_task_comment, delete_task, update_task_details,
    update_task_description, bulk_delete_tasks,
    get_task_details, move_task, get_task_count,
    get_task_comments, update_task_comment, delete_task_comment,
    get_task_associated_bugs, associate_bugs_to_task, disassociate_bug_from_task,
    get_task_status_timeline,
)
from app.tools.bugs import (
    list_project_bugs, create_bug, update_bug, delete_bug, get_bug_details,
    get_bug_activities, move_bug,
    link_bugs, unlink_bugs, get_linked_bugs,
    get_bug_associated_tasks, associate_tasks_to_bug,
    disassociate_task_from_bug,
    get_bug_resolution, add_bug_resolution, update_bug_resolution, delete_bug_resolution,
    get_bug_comments, add_bug_comment, update_bug_comment, delete_bug_comment,
)
from app.tools.milestones import list_project_milestones
from app.tools.timelogs import (
    create_time_log, update_time_log, delete_time_log,
    get_project_timelogs, get_portal_timelogs, get_time_log_details,
    bulk_add_time_logs, bulk_update_time_logs, bulk_delete_time_logs,
)
from app.tools.members import list_project_members, add_user_to_project
from app.tools.tasklists import list_task_lists, get_current_datetime, create_task_list


def get_tools() -> list:    # Return list of all available tools for the LangChain agent
    return [
        list_active_projects, get_project_details, create_project, update_project,
        list_project_tasks, create_task_on_project, update_task_status,
        assign_task_to_user, update_task_priority, set_task_due_date,
        add_task_comment, delete_task, update_task_details,
        update_task_description, bulk_delete_tasks, add_user_to_project,
        get_task_details, move_task, get_task_count,
        get_task_comments, update_task_comment, delete_task_comment,
        get_task_associated_bugs, associate_bugs_to_task, disassociate_bug_from_task,
        get_task_status_timeline,
        # Bug / Issue tools
        list_project_bugs, create_bug, update_bug, delete_bug, get_bug_details,
        get_bug_activities, move_bug,
        link_bugs, unlink_bugs, get_linked_bugs,
        get_bug_associated_tasks, associate_tasks_to_bug, disassociate_task_from_bug,
        get_bug_resolution, add_bug_resolution, update_bug_resolution, delete_bug_resolution,
        get_bug_comments, add_bug_comment, update_bug_comment, delete_bug_comment,
        list_project_milestones,
        create_time_log, update_time_log, delete_time_log,
        get_project_timelogs, get_portal_timelogs, get_time_log_details,
        bulk_add_time_logs, bulk_update_time_logs, bulk_delete_time_logs,
        list_project_members,
        list_task_lists, get_current_datetime, create_task_list,
    ]


__all__ = [
    "get_tools",
    "list_active_projects", "get_project_details", "create_project", "update_project",
    "list_project_tasks", "create_task_on_project", "update_task_status",
    "assign_task_to_user", "update_task_priority", "set_task_due_date",
    "add_task_comment", "delete_task", "update_task_details",
    "update_task_description", "bulk_delete_tasks", "add_user_to_project",
    "get_task_details", "move_task", "get_task_count",
    "get_task_comments", "update_task_comment", "delete_task_comment",
    "get_task_associated_bugs", "associate_bugs_to_task", "disassociate_bug_from_task",
    "get_task_status_timeline",
    "list_project_bugs", "create_bug", "update_bug", "delete_bug", "get_bug_details",
    "get_bug_activities", "move_bug",
    "link_bugs", "unlink_bugs", "get_linked_bugs",
    "get_bug_associated_tasks", "associate_tasks_to_bug", "disassociate_task_from_bug",
    "get_bug_resolution", "add_bug_resolution", "update_bug_resolution", "delete_bug_resolution",
    "get_bug_comments", "add_bug_comment", "update_bug_comment", "delete_bug_comment",
    "list_project_milestones",
    "create_time_log", "update_time_log", "delete_time_log",
    "get_project_timelogs", "get_portal_timelogs", "get_time_log_details",
    "bulk_add_time_logs", "bulk_update_time_logs", "bulk_delete_time_logs",
    "list_project_members",
    "list_task_lists", "get_current_datetime", "create_task_list",
]
