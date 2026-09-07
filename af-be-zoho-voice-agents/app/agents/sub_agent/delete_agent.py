"""Delete sub-agent — removes tasks, bugs, comments, timelogs, and unlinks associations."""
from langchain.agents import create_agent

from app.agents.model import model
from app.prompts import SYSTEM_PROMPT, TOOL_MANDATE
from app.tools.projects import list_active_projects
from app.tools.tasks import (
    list_project_tasks, get_task_comments,
    delete_task, bulk_delete_tasks, delete_task_comment, disassociate_bug_from_task,
)
from app.tools.bugs import (
    list_project_bugs, get_bug_comments, get_linked_bugs,
    delete_bug, delete_bug_comment, delete_bug_resolution,
    unlink_bugs, disassociate_task_from_bug,
)
from app.tools.timelogs import get_project_timelogs, delete_time_log, bulk_delete_time_logs, fetch_timelogs

delete_agent = create_agent(
    model=model,
    tools=[
        list_active_projects,
        list_project_tasks, get_task_comments,
        delete_task, bulk_delete_tasks, delete_task_comment, disassociate_bug_from_task,
        list_project_bugs, get_bug_comments, get_linked_bugs,
        delete_bug, delete_bug_comment, delete_bug_resolution,
        unlink_bugs, disassociate_task_from_bug,
        get_project_timelogs, delete_time_log, bulk_delete_time_logs, fetch_timelogs,
    ],
    system_prompt=TOOL_MANDATE + "\n\n" + SYSTEM_PROMPT + "\n\nOPERATION CONSTRAINT: You are a delete agent. Remove or unlink entities only. Always confirm destructive actions before executing.",
    name="delete_agent",
)
