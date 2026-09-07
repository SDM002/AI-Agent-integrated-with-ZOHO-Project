"""Add sub-agent — attaches comments, links, associations, and assignments to existing entities."""
from langchain.agents import create_agent

from app.agents.model import model
from app.prompts import SYSTEM_PROMPT, TOOL_MANDATE
from app.tools.projects import list_active_projects
from app.tools.tasks import (
    list_project_tasks, add_task_comment,
    associate_bugs_to_task, assign_task_to_user,
)
from app.tools.bugs import (
    list_project_bugs,
    add_bug_comment, add_bug_resolution,
    link_bugs,
    associate_tasks_to_bug,
    update_bug,
)
from app.tools.members import list_project_members, add_user_to_project

add_agent = create_agent(
    model=model,
    tools=[
        list_active_projects,
        list_project_tasks, add_task_comment,
        associate_bugs_to_task, assign_task_to_user,
        list_project_bugs,
        add_bug_comment, add_bug_resolution,
        link_bugs,
        associate_tasks_to_bug,
        update_bug,
        list_project_members, add_user_to_project,
    ],
    system_prompt=TOOL_MANDATE + "\n\n" + SYSTEM_PROMPT + "\n\nOPERATION CONSTRAINT: You are an add agent. Add comments, links, associations, and assignments to existing entities only. Never create top-level entities or delete anything.",
    name="add_agent",
)
