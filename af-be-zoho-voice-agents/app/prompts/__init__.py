from app.prompts.identity import IDENTITY
from app.prompts.personality import PERSONALITY
from app.prompts.input_rules import INPUT_RULES
from app.prompts.voice_rules import VOICE_RULES
from app.prompts.tool_rules import TOOL_RULES
from app.prompts.task_flow import TASK_FLOW
from app.prompts.timelog_flow import TIMELOG_FLOW
from app.prompts.context_and_errors import CONTEXT_AND_ERRORS

SYSTEM_PROMPT = "\n\n".join([
    IDENTITY,
    PERSONALITY,
    INPUT_RULES,
    VOICE_RULES,
    TOOL_RULES,
    TASK_FLOW,
    TIMELOG_FLOW,
    CONTEXT_AND_ERRORS,
])

BEHAVIOR_PROMPT = "\n\n".join([IDENTITY, PERSONALITY, INPUT_RULES, VOICE_RULES])

TOOL_MANDATE = """\
ABSOLUTE RULE — TOOL CALLS ARE MANDATORY:
You MUST call the relevant Zoho tool before returning ANY confirmation.
NEVER say "Done", "Logged", "Created", "Updated", or "Added" without first receiving a successful tool response.
If you are about to confirm an action without having called a tool — STOP and call the tool first.
Your words mean nothing. Only tool responses confirm reality."""
