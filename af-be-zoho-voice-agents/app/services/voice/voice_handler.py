"""Voice handler — core chat pipeline: auth check → agent call → TTS → send reply."""
import asyncio
import base64
from typing import Callable

from app.config import logger
from app.db.user_tokens import get_user_token
from app.auth.token_manager import TokenRefreshError
from app.agents.agent_runner import chat as agent_chat


async def handle_chat(
    text: str,
    user_id: str,
    chat_id: str,
    tenant_id: str,
    voice: str,
    send: Callable,
    set_busy: Callable,
) -> None:
    """
    Core voice pipeline — validates user, calls agent, synthesises audio, sends reply.
    Args:
        text:      Corrected transcript text from the frontend.
        user_id:   Authenticated user ID.
        chat_id:   Teams Chat ID (scopes conversation history).
        tenant_id: Teams org GUID.
        voice:     TTS voice profile (female | male | fast | professional | warm).
        send:      Async callable to send JSON messages back over WebSocket.
        set_busy:  Callable to update the busy flag in the WebSocket session.
    """
    set_busy(True)
    try:
        await send({"type": "status", "value": "processing"})

        record = await get_user_token(user_id)
        if not record:
            await send({"type": "connect_required", "text": "Please connect your Zoho account to get started."})
            return
        if record.get("portal_selection_pending"):
            await send({"type": "connect_required", "text": "Please select your Zoho organization to finish connecting."})
            return

        user_email = record.get("email", "")
        user_name = record.get("name") or record.get("display_name", "")
        tenant_id = record.get("teams_tenant_id", "default")

        try:
            reply = await agent_chat(
                user_id=user_id,
                user_input=text,
                chat_id=chat_id,
                tenant_id=tenant_id,
                user_email=user_email,
                user_name=user_name,
            )
        except TokenRefreshError:
            await send({"type": "connect_required", "text": "Your Zoho session has expired. Please reconnect."})
            return
        except asyncio.TimeoutError:
            reply = "Sorry, that took too long. Please try again."
        except Exception as e:
            if isinstance(e, TokenRefreshError) or ("token" in str(e).lower() and "refresh" in str(e).lower()):
                await send({"type": "connect_required", "text": "Your Zoho session has expired. Please reconnect."})
                return
                
            error_msg = str(e).lower()
            if "badrequest" in error_msg or "invalid message" in error_msg or "tool call" in error_msg or "400" in error_msg:
                reply = "This conversation has gotten too long and my memory is full. Please click 'New Chat' to start fresh!"
            else:
                logger.error("Agent error", user=user_id, error=str(e))
                reply = "Sorry, something went wrong. Please try again."

        await send({"type": "status", "value": "speaking"})

        b64 = None
        try:
            from app.voice.tts.tts import tts, clean_for_speech
            wav = await asyncio.to_thread(tts.synthesize, clean_for_speech(reply), voice=voice)
            if wav:
                b64 = base64.b64encode(wav).decode()
        except Exception:
            pass

        await send({"type": "reply", "text": reply, "audio_b64": b64, "audio_mime": "audio/wav"})

    except Exception as e:
        logger.error("handle_chat error", user=user_id, error=str(e))
    finally:
        set_busy(False)
        await send({"type": "status", "value": "listening"})
