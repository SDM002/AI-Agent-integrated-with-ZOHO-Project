"""Supervisor agent responsible for routing user requests to appropriate sub-agents using langgraph-supervisor."""

from langgraph_supervisor import create_supervisor, create_handoff_tool

from app.agents.model import model
from app.prompts import BEHAVIOR_PROMPT
from app.agents.sub_agent.get_agent import get_agent
from app.agents.sub_agent.create_agent import creation_agent
from app.agents.sub_agent.add_agent import add_agent
from app.agents.sub_agent.update_agent import update_agent
from app.agents.sub_agent.delete_agent import delete_agent
from app.agents.middleware import trim_messages_middleware, tool_retry_middleware

SUPERVISOR_PROMPT = BEHAVIOR_PROMPT + """

You are a supervisor agent responsible for routing user requests to the correct sub-agent.

You do NOT perform tasks yourself.
You MUST delegate every request to exactly one sub-agent.

Available sub-agents:

1. GET agent (read-only)
- Use for fetching or viewing data
- Examples: list, get details, view comments, check status, retrieve information, current date and time

2. CREATE agent (new entities)
- Use for creating new top-level objects
- Examples: create task, create bug, create project, create task list, create time log

3. ADD agent (attach or associate)
- Use for adding something to an existing entity
- Examples: add comment, add resolution to bug, link bugs, assign user, associate tasks or bugs
- IMPORTANT: "add resolution" always goes to ADD agent, even when the user also asks to set a status

4. UPDATE agent (modify existing)
- Use for changing or editing existing data
- Examples: update task, change status, edit comment, update bug, move item

5. DELETE agent (remove or unlink)
- Use for deleting or removing data
- Examples: delete task, delete bug, remove comment, unlink items

Routing Rules:
- Always choose exactly ONE agent
- NEVER call multiple agents at once. NEVER make parallel tool calls in the same turn.
- CRITICAL: NEVER break apart a single user request into multiple sub-agent calls. If the user asks to create or log MULTIPLE things at once, you MUST pass the ENTIRE message as a single string to the sub-agent in ONE single tool call. Let the sub-agent handle the bulk processing.
- Never answer directly — ALWAYS delegate, even for short replies like "yes", "no", "skip", or a single word
- If the request is unclear, choose the most likely agent based on intent

CRITICAL — Context forwarding (NON-NEGOTIABLE FORMAT):
Every message you receive starts with [Today is DATE] and [Current user's email: EMAIL].
When you call a sub-agent, copy BOTH tags verbatim to the very start of the input string — character for character, unchanged.

The action description goes AFTER the tags. The user's email address MUST NOT appear anywhere inside the action sentence.
- Do NOT write "for [email]", "for [name]@...", or any email address in the action text.
- If the user said "for me" or "for myself", omit it — the [Current user's email:] tag already identifies the owner.
- Sub-agents read the [Current user's email:] tag to determine ownership. If you embed the email inside the action sentence, the sub-agent will interpret it as a request on behalf of a different user and refuse.

Never strip, reword, or paraphrase the context tags. Sub-agents depend on them for date resolution and user identification.

RESPONSE FORWARDING — NON-NEGOTIABLE:
Return the sub-agent's reply to the user EXACTLY as received — word for word.
NEVER summarise, paraphrase, shorten, or reword it.
Your only job after delegation is to pass the result through unchanged.

Be concise and precise when delegating."""

supervisor = None  # set during app startup via init_supervisor()

# Supervisor agent initializing the multi-agent orchestration layer with routing logic, tools, state management
def init_supervisor():
    global supervisor
    from app.services.checkpoint import checkpointer
    
    handoff_tools = [
        create_handoff_tool(
            agent_name="get_agent",
            name="assign_to_get_agent",
            description="Read-only agent. Use for fetching or viewing any data — list, get details, view comments, check status."
        ),
        create_handoff_tool(
            agent_name="creation_agent",
            name="assign_to_creation_agent",
            description="Creation agent. Use for creating new top-level objects — task, bug, project, task list, time log."
        ),
        create_handoff_tool(
            agent_name="add_agent",
            name="assign_to_add_agent",
            description="Add agent. Use for attaching or associating things to existing entities — add comment, link bugs, assign user."
        ),
        create_handoff_tool(
            agent_name="update_agent",
            name="assign_to_update_agent",
            description="Update agent. Use for modifying existing data — update task, change status, edit comment, move item."
        ),
        create_handoff_tool(
            agent_name="delete_agent",
            name="assign_to_delete_agent",
            description="Delete agent. Use for deleting or removing any data."
        ),
    ]

    workflow = create_supervisor(
        agents=[get_agent, creation_agent, add_agent, update_agent, delete_agent],
        model=model,
        tools=handoff_tools,
        prompt=SUPERVISOR_PROMPT,
        output_mode="last_message",
    )

    # Note: langgraph-supervisor compile takes checkpointer argument
    supervisor = workflow.compile(
        checkpointer=checkpointer,
    )
