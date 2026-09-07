"""
FastAPI Application — entrypoint for Zoho PM Agent.

Responsibilities:
- Exposes HTTP and WebSocket endpoints
- Handles request validation and rate limiting
- Manages user session mapping (chat_id ↔ user_id ↔ tenant_id)
- Routes chat requests to the agent orchestrator
- Manages application lifecycle (startup/shutdown)
"""
import asyncio
import base64
import time
import uuid
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import SETTINGS, logger, setup_logging
from app.db.user_tokens import get_user_token
from app.db.chat_sessions import save_chat_session
from app.db.indexes import ensure_indexes
from app.agents.agent_runner import chat as agent_chat
from app.services.checkpoint import init_checkpointer, close_checkpointer
from app.services.http_client import init_http_client, close_http_client
from app.db.redis import get_redis, close_redis
from app.routes.voice_ws import router as voice_ws_router
from app.routes.auth_routes import router as auth_router
from app.auth.token_manager import TokenRefreshError


# -- Request Tracing Middleware ( Adds request_id, tracks latency, and logs request lifecycle )
class RequestTracingMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        request_id = ""
        for name, value in scope.get("headers", []):
            if name == b"x-request-id":
                request_id = value.decode()
                break
        if not request_id:
            request_id = str(uuid.uuid4())[:8]

        scope.setdefault("state", {})["request_id"] = request_id
        start = time.monotonic()
        status_code = 0

        async def send_with_tracking(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                message = {**message, "headers": headers}
            elif message["type"] == "http.response.body" and not message.get("more_body"):
                duration_ms = int((time.monotonic() - start) * 1000)
                logger.info(
                    "request completed",
                    request_id=request_id,
                    method=scope.get("method", ""),
                    path=scope.get("path", ""),
                    status=status_code,
                    duration_ms=duration_ms,
                )
            await send(message)

        await self.app(scope, receive, send_with_tracking)


# --- Per-User Rate Limiting (Redis sorted-set sliding window — multi-pod safe)
RATE_LIMIT_MAX_CALLS = SETTINGS.RATE_LIMIT_MAX_CALLS
RATE_LIMIT_WINDOW_SECS = SETTINGS.RATE_LIMIT_WINDOW_SECS

async def check_rate_limit(user_id: str) -> None:
    r = await get_redis()
    key = f"rate:{user_id}"
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW_SECS
    member = f"{now}:{uuid.uuid4()}"  # unique member so concurrent requests don't collide

    async with r.pipeline(transaction=True) as pipe:
        pipe.zremrangebyscore(key, "-inf", window_start)        # drop expired entries
        pipe.zadd(key, {member: now})                           # record this request
        pipe.zcard(key)                                          # count in window
        pipe.zrange(key, 0, 0, withscores=True)                 # oldest entry (for Retry-After)
        pipe.expire(key, int(RATE_LIMIT_WINDOW_SECS) + 1)       # auto-clean idle keys
        results = await pipe.execute()

    count = results[2]
    if count > RATE_LIMIT_MAX_CALLS:
        oldest_entries = results[3]
        if oldest_entries:
            retry_after = int(RATE_LIMIT_WINDOW_SECS - (now - oldest_entries[0][1])) + 1
        else:
            retry_after = int(RATE_LIMIT_WINDOW_SECS)
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {RATE_LIMIT_MAX_CALLS} requests per minute.",
            headers={"Retry-After": str(retry_after)},
        )

# --- Application Lifespan (Startup / Shutdown):Initializes DB indexes, checkpointer, HTTP client, and TTS engine
@asynccontextmanager
async def lifespan(application: FastAPI):
    setup_logging()

    await get_redis()
    await ensure_indexes()
    await init_checkpointer()
    from app.agents.supervisor import init_supervisor
    init_supervisor()
    logger.info("Supervisor initialised")
    init_http_client()

    try:
        from app.voice.tts.tts import tts
        tts.load()
    except Exception as e:
        logger.warning("TTS unavailable", error=str(e))

    logger.info(
        "Server ready",
        environment=SETTINGS.ENVIRONMENT,
        port=SETTINGS.APP_PORT,
        deployment=SETTINGS.AZURE_OPENAI_DEPLOYMENT,
    )

    yield

    await close_checkpointer()
    await close_http_client()
    await close_redis()
    logger.info("Server shutdown complete")


# ── FastAPI App Initialization (Configures CORS, middleware, and route registration)
app = FastAPI(title="Zoho Voice Logger API", version="2.0.0", lifespan=lifespan)

cors_origins = [o.strip() for o in SETTINGS.CORS_ORIGINS.split(",") if o.strip()]

# If wildcard is used, use regex to bypass Starlette's exact-match restriction with credentials
if "*" in cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=".*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.add_middleware(RequestTracingMiddleware)

app.include_router(voice_ws_router)
app.include_router(auth_router)


# -- API Routes--- Health Check and Chat Endpoint
@app.get("/api/health")
async def health():
    return {"status": "ok", "environment": SETTINGS.ENVIRONMENT}


@app.post("/api/chat")
async def chat( # Handles chat requests and routes them to the agent
    message: str = Form(...),
    user_id: str = Form(default=SETTINGS.DEFAULT_USER_ID),
    chat_id: str = Form(default=""),        # Teams Chat ID — the real session identifier
    tenant_id: str = Form(default=""),      # Teams org GUID
    include_audio: bool = Form(default=False),
    voice: str = Form(default="female"),
):
    user_id = user_id.lower()
    await check_rate_limit(user_id)

    record = await get_user_token(user_id)
    if not record:
        return JSONResponse({"action": "connect_required", "reply": "Please connect your Zoho account to get started."})

    if record.get("portal_selection_pending"):
        return JSONResponse({"action": "connect_required", "reply": "Please select your Zoho organization to finish connecting."})

    user_email = record.get("email", "")
    # Prefer form-supplied tenant_id (Teams org GUID); fall back to stored value
    resolved_tenant_id = tenant_id or record.get("teams_tenant_id", "default")
    # Prefer form-supplied chat_id (Teams Chat ID); fall back to user_id for web context
    resolved_chat_id = chat_id or user_id

    # Persist the session: chat_id → user_id + tenant_id
    await save_chat_session(
        chat_id=resolved_chat_id,
        tenant_id=resolved_tenant_id,
        user_id=user_id,
    )

    user_name = record.get("name") or record.get("display_name", "")

    try:
        reply = await agent_chat(
            user_id=user_id,
            user_input=message,
            chat_id=resolved_chat_id,
            tenant_id=resolved_tenant_id,
            user_email=user_email,
            user_name=user_name,
        )
    except asyncio.TimeoutError:
        return JSONResponse({"reply": "Sorry, that took too long. Please try again."})
    except Exception as e:
        if isinstance(e, TokenRefreshError) or ("token" in str(e).lower() and "refresh" in str(e).lower()):
            return JSONResponse({"action": "connect_required", "reply": "Your Zoho session has expired. Please reconnect."})
            
        error_msg = str(e).lower()
        if "badrequest" in error_msg or "invalid message" in error_msg or "tool call" in error_msg or "400" in error_msg:
            return JSONResponse({"reply": "This conversation has gotten too long and my memory is full. Please click 'New Chat' to start fresh!"})
            
        logger.error("Chat error", user=user_id, error=str(e))
        return JSONResponse({"reply": "Sorry, something went wrong. Please try again."})

    response: dict = {"reply": reply}

    if include_audio:
        try:
            from app.voice.tts.tts import tts, clean_for_speech
            wav = await asyncio.to_thread(tts.synthesize, clean_for_speech(reply), voice=voice)
            if wav:
                response["audio_base64"] = base64.b64encode(wav).decode()
                response["audio_mime"] = "audio/wav"
        except Exception:
            pass

    return response
