"""Read-only sub-agent — fetches projects, tasks, bugs, timelogs, members, and milestones."""
from langchain.agents import create_agent

from app.agents.model import model
from app.prompts import SYSTEM_PROMPT, TOOL_MANDATE
from app.tools.projects import list_active_projects, get_project_details
from app.tools.tasks import (
    list_project_tasks, get_task_details, get_task_comments,

    get_task_count, get_task_status_timeline, get_task_associated_bugs,
)
from app.tools.bugs import (
    list_project_bugs, get_bug_details, get_bug_comments,
    get_bug_activities, get_bug_resolution, get_bug_associated_tasks, get_linked_bugs,
)
from app.tools.timelogs import (
    get_project_timelogs, get_portal_timelogs, get_time_log_details,
    fetch_timelogs, get_daily_timelog_summary, get_timelogs_for_date
)
from app.tools.milestones import list_project_milestones
from app.tools.members import list_project_members
from app.tools.tasklists import list_task_lists, get_current_datetime

get_agent = create_agent(
    model=model,
    tools=[
        list_active_projects, get_project_details,
        list_project_tasks, get_task_details, get_task_comments,
        get_task_count, get_task_status_timeline, get_task_associated_bugs,
        list_project_bugs, get_bug_details, get_bug_comments,
        get_bug_activities, get_bug_resolution, get_bug_associated_tasks, get_linked_bugs,
        get_project_timelogs, get_portal_timelogs, get_time_log_details, fetch_timelogs, get_daily_timelog_summary, get_timelogs_for_date,
        list_project_milestones,
        list_project_members,
        list_task_lists, get_current_datetime,
    ],
    system_prompt=TOOL_MANDATE + "\n\n" + SYSTEM_PROMPT + "\n\nOPERATION CONSTRAINT: You are a read-only agent. Fetch and return data only. Never create, modify, or delete anything.\n\nFORMATTING MANDATE: When presenting retrieved time logs, you MUST format them as a Markdown table. Use the following columns:\n\n| Project | Type | Task / Log Name | Log Hours | Time Period | Billing Type |\n|---|---|---|---|---|---|\n| [Project Name] | Task / General | [Task or Log Name] | [N hrs M min] | [Start] to [End] / — | Billable / Non-billable |\n\nRules:\n1. 'Type' column: use 'Task' if linked to a task, 'General' if it is a general log.\n2. 'Task / Log Name': use the task name for task logs, or the log title for general logs.\n3. 'Time Period': use '[Start Time] to [End Time]'. If start/end times are missing, use '—'.\n4. 'Log Hours': express as '[N] hr [M] min' (e.g. '1 hr 30 min'). If only hours, use '[N] hr'.\n5. Group all logs for the same project together in consecutive rows.\n6. NEVER use bullet points or plain text for timelog output. Always use the table format above.",
    name="get_agent",
)
