"""Middleware for LangChain agents: trims message history and handles tool retries."""
from langchain.agents.middleware import wrap_model_call, ToolRetryMiddleware
from langchain_core.messages import trim_messages, ToolMessage
from app.config import SETTINGS

tool_retry_middleware = ToolRetryMiddleware(
    max_retries=SETTINGS.TOOL_RETRY_MAX_RETRIES,
    backoff_factor=SETTINGS.TOOL_RETRY_BACKOFF_FACTOR,
    initial_delay=SETTINGS.TOOL_RETRY_INITIAL_DELAY,
    on_failure="return_message",
    jitter=SETTINGS.TOOL_RETRY_JITTER,
)

@wrap_model_call
async def trim_messages_middleware(request, handler):
    msgs = [m for m in request.messages if not (
        hasattr(m, "tool_calls") and m.tool_calls and
        any(tc["id"] not in {t.tool_call_id for t in request.messages if isinstance(t, ToolMessage)} for tc in m.tool_calls)
    )]  # Drop AI messages with unanswered tool_calls — prevents 400 from broken checkpoints
    return await handler(request.override(messages=trim_messages(
        msgs,
        max_tokens=SETTINGS.AGENT_MEMORY_WINDOW,
        strategy="last",
        token_counter=len,
        include_system=True,
        start_on="human",
        allow_partial=False,
    )))
