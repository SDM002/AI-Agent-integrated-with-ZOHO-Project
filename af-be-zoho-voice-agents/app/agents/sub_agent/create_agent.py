"""Creation sub-agent — creates new projects, tasks, bugs, timelogs, and task lists."""
from langchain.agents import create_agent

from app.agents.model import model
from app.prompts import SYSTEM_PROMPT, TOOL_MANDATE
from app.tools.projects import list_active_projects, create_project
from app.tools.tasks import list_project_tasks, create_task_on_project
from app.tools.bugs import list_project_bugs, create_bug
from app.tools.timelogs import create_time_log, get_project_timelogs, bulk_add_time_logs, get_timelogs_for_date
from app.tools.tasklists import list_task_lists, create_task_list, get_current_datetime

creation_agent = create_agent(
    model=model,
    tools=[
        list_active_projects, create_project,
        list_project_tasks, create_task_on_project,
        list_project_bugs, create_bug,
        create_time_log, get_project_timelogs, bulk_add_time_logs, get_timelogs_for_date,
        list_task_lists, create_task_list,
        get_current_datetime,
    ],
    system_prompt=TOOL_MANDATE + "\n\n" + SYSTEM_PROMPT + "\n\nOPERATION CONSTRAINT: You are a creation agent. Create new entities only. Never modify or delete existing data.",
    name="creation_agent",
)
