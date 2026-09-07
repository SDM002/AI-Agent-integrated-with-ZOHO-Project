"""Update sub-agent — modifies existing tasks, bugs, comments, timelogs, and projects."""
from langchain.agents import create_agent

from app.agents.model import model
from app.prompts import SYSTEM_PROMPT, TOOL_MANDATE
from app.tools.projects import list_active_projects, update_project
from app.tools.tasks import (
    list_project_tasks, get_task_details, get_task_comments,
    update_task_status, update_task_priority, update_task_description,
    update_task_details, update_task_comment, set_task_due_date, move_task,
)
from app.tools.bugs import (
    list_project_bugs, get_bug_details, get_bug_comments,
    update_bug, update_bug_comment, update_bug_resolution,
    move_bug,
)
from app.tools.timelogs import update_time_log, get_project_timelogs, bulk_update_time_logs, fetch_timelogs, get_timelogs_for_date
from app.tools.tasklists import get_current_datetime

update_agent = create_agent(
    model=model,
    tools=[
        list_active_projects, update_project,
        list_project_tasks, get_task_details, get_task_comments,
        update_task_status, update_task_priority, update_task_description,
        update_task_details, update_task_comment, set_task_due_date, move_task,
        list_project_bugs, get_bug_details, get_bug_comments,
        update_bug, update_bug_comment, update_bug_resolution,
        move_bug,
        get_project_timelogs,
        update_time_log,
        bulk_update_time_logs,
        fetch_timelogs,
        get_timelogs_for_date,
        get_current_datetime,
    ],
    system_prompt=TOOL_MANDATE + "\n\n" + SYSTEM_PROMPT + "\n\nOPERATION CONSTRAINT: You are an update agent. Modify existing entities only. Never create new entities or delete anything.\n\nFORMATTING MANDATE: When confirming updates, present a Markdown table showing the previous and new values if the tool provides them. Columns: | Field | Previous Value | New Value |. Use 'Unknown' if the previous value is not provided by the tool.",
    name="update_agent",
)
