"""Transcript correction — fixes speech-to-text errors using the shared LLM before agent processing."""
from langchain_core.messages import SystemMessage, HumanMessage

from app.config import logger
from app.agents.model import model

CORRECTION_PROMPT = """You are a voice transcript corrector for a Zoho Projects AI assistant.
Fix speech-to-text errors and return ONLY the corrected text. No explanations.
Common fixes: "add a new dog/doc/dock" → "add a new task", "Hai Joho" → "Hey Zoho".
Do NOT change correctly transcribed words. Do NOT remove user instructions."""


async def correct_transcript(raw: str) -> str:
    """Fix STT errors using the shared LLM (pre-processing step before main agent)."""
    try:
        result = await model.ainvoke([
            SystemMessage(content=CORRECTION_PROMPT),
            HumanMessage(content=raw),
        ])
        return result.content.strip()
    except Exception as e:
        logger.warning("Transcript correction failed, using raw input", error=str(e))
        return raw
