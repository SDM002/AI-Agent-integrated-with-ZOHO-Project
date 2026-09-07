"""Chat entry point — sets request context, invokes the supervisor, and returns the final reply."""

import asyncio
from datetime import datetime

import app.agents.supervisor as supervisor_module
from app.config import SETTINGS, logger
from app.db.client import get_db
from app.db.checkpoints import touch_checkpoint_ttl
from app.utils.request_context import set_user_id, set_request_context

# === Entry Point: Chat Orchestration ===
async def chat(  
    user_id: str,
    user_input: str,
    chat_id: str,
    tenant_id: str,
    user_email: str = None,
    user_name: str = None,
) -> str: #Build request context, execute supervisor agent with timeout, and return final reply.---
    set_user_id(user_id) # ---Step 1: Initialize User Context ---

    today = datetime.now().strftime("%A, %B %d, %Y") #--- Step 2: Build Request Context (Date + User Info) ---
    context = f"[Today is {today}]"
    if user_name:
        context += f" [Current user's name: {user_name}]"
    if user_email:
        context += f" [Current user's email: {user_email}]"
    set_request_context(context)

    thread_id = f"{tenant_id}:{chat_id}"   # --- Step 3: Generate Thread ID (Tenant + Chat Scope)----

    logger.info(f"\n[{user_email or user_id}] User Input: {user_input}") # --- Step 4: Log Incoming User Input ---

    try:                                                     # --- Step 5: Invoke Supervisor Agent (with Timeout Protection) ----
        async with asyncio.timeout(SETTINGS.AGENT_TIMEOUT):
            result = await supervisor_module.supervisor.ainvoke(
                {"messages": [{"role": "user", "content": f"{context} {user_input}"}]},
                config={"configurable": {"thread_id": thread_id}},
            )
    finally:
        await touch_checkpoint_ttl(get_db(), thread_id) # ---Step 6: Refresh Checkpoint TTL — always runs, even on crash --

    reply = result["messages"][-1].content  #--- Step 7: Extract Final Response from Agent Output ---
    logger.info("Agent reply", tenant=tenant_id, user=user_id, chat=chat_id) # ---Step 8: Log Agent Response Metadata ---
    return reply
