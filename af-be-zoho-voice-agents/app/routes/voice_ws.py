"""
Voice WebSocket Route — manages real-time voice sessions, message routing,
and interaction between frontend and voice processing services.
"""
import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import SETTINGS, logger
from app.db.chat_sessions import save_chat_session
from app.services.voice.voice_handler import handle_chat
from app.services.voice.transcript_correction import correct_transcript

router = APIRouter()

# WebSocket entrypoint for voice interactions — handles session setup,message routing, transcript correction, and interruption control. 
@router.websocket("/ws/voice")
async def voice_ws(websocket: WebSocket):
    await websocket.accept()

    # Session state — set via "config" message from frontend
    user_id   = SETTINGS.DEFAULT_USER_ID
    tenant_id = ""
    chat_id   = ""
    voice     = SETTINGS.DEFAULT_VOICE
    busy      = False
   
    # --Outgoing Message Helper
    async def send(obj: dict) -> None:
        """Safely send JSON messages to frontend via WebSocket."""
        try:
            await websocket.send_json(obj)
        except Exception:
            pass
    # ---Busy State Controller
    def set_busy(value: bool) -> None:
        nonlocal busy
        busy = value
    
    # -- Initial Status
    await send({"type": "status", "value": "listening"})

    try:
        while True: # -- Main Receive Loop
            try:
                msg = await asyncio.wait_for(websocket.receive(), timeout=SETTINGS.WS_RECEIVE_TIMEOUT)
            except asyncio.TimeoutError:
                await send({"type": "ping"})
                continue

            if msg["type"] == "websocket.disconnect":
                break

            if not msg.get("text"):
                continue

            try:
                d = json.loads(msg["text"])
                t = d.get("type", "")

                if t == "config":
                    user_id   = d.get("user_id", user_id).lower()
                    tenant_id = d.get("tenant_id", tenant_id)
                    chat_id   = d.get("chat_id") or d.get("session_id") or chat_id or user_id
                    voice     = d.get("voice", voice)
                    logger.info("WS session configured", user=user_id, tenant=tenant_id, chat=chat_id)
                    await save_chat_session(chat_id=chat_id, tenant_id=tenant_id, user_id=user_id)

                elif t == "chat":
                    text = d.get("text", "").strip()
                    if text and not busy:
                        asyncio.create_task(handle_chat(
                            text=text,
                            user_id=user_id,
                            chat_id=chat_id,
                            tenant_id=tenant_id,
                            voice=voice,
                            send=send,
                            set_busy=set_busy,
                        ))
                    elif text and busy:
                        logger.warning("Message dropped — agent busy", user=user_id)

                elif t == "correct":
                    raw = d.get("text", "").strip()
                    if raw:
                        corrected = await correct_transcript(raw)
                        await send({"type": "transcript_corrected", "text": corrected})

                elif t == "interrupt":
                    busy = False
                    await send({"type": "interrupted"})
                    await send({"type": "status", "value": "listening"})

                elif t == "ping":
                    await send({"type": "pong"})

            except Exception as e:
                logger.error("WS message error", error=str(e))

    except WebSocketDisconnect:
        pass
    finally:
        logger.info("WS disconnected", user=user_id)
