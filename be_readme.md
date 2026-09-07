# Zoho PM Agent — Backend

A production-grade AI assistant for Zoho Projects. Users send natural-language messages (text or voice) from Microsoft Teams or any HTTP client; the backend resolves those into real Zoho API actions — create tasks, log time, manage bugs, assign members, track projects — and replies in plain English.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Tech Stack](#2-tech-stack)
3. [Full Request Cycle](#3-full-request-cycle)
4. [Agent Architecture](#4-agent-architecture)
5. [Voice AI Flow](#5-voice-ai-flow)
6. [OAuth & Token Flow](#6-oauth--token-flow)
7. [Caching — All Layers End to End](#7-caching--all-layers-end-to-end)
8. [MongoDB — What Is Stored, How, and What Is Encrypted](#8-mongodb--what-is-stored-how-and-what-is-encrypted)
9. [Multi-Tenant & Multi-User Architecture](#9-multi-tenant--multi-user-architecture)
10. [Resolvers — Why Name Resolution Exists](#10-resolvers--why-name-resolution-exists)
11. [Tools Reference](#11-tools-reference)
12. [File Architecture](#12-file-architecture)
13. [API Endpoints](#13-api-endpoints)
14. [WebSocket Protocol](#14-websocket-protocol)
15. [Configuration Reference](#15-configuration-reference)
16. [Local Setup](#16-local-setup)
17. [Common Errors](#17-common-errors)
18. [Security Notes](#18-security-notes)

---

## 1. Architecture Overview

```
Microsoft Teams / Web Frontend
        │  HTTP POST /api/chat  (or WebSocket /ws/voice)
        ▼
┌───────────────────────────────────────────────────────────────────┐
│                          FastAPI App                              │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │  CORS + RequestTracingMiddleware + RateLimiter (per user)    │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                              │                                    │
│                              ▼                                    │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │              Supervisor Agent  (app/agents/supervisor.py)    │ │
│  │                                                              │ │
│  │  AzureChatOpenAI  ──►  Routes to correct sub-agent          │ │
│  │        │                                                     │ │
│  │        ├── get_agent_tool    → GET Agent  (read-only)        │ │
│  │        ├── create_agent_tool → CREATE Agent (new entities)   │ │
│  │        ├── add_agent_tool    → ADD Agent  (attach/link)      │ │
│  │        ├── update_agent_tool → UPDATE Agent (modify)         │ │
│  │        └── delete_agent_tool → DELETE Agent (remove)         │ │
│  │                                                              │ │
│  │  Each sub-agent runs its own LLM + tool loop                 │ │
│  │  Middleware: [trim_messages_middleware, tool_retry_middleware]│ │
│  └──────────────────────────────────────────────────────────────┘ │
│                              │                                    │
│                   tool calls resolved by                          │
│                              │                                    │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │                  Tools Layer (~57 @tool functions)           │ │
│  │  projects · tasks · bugs · milestones · members ·            │ │
│  │  timelogs · tasklists                                        │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                              │                                    │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │         ZohoHttpClient  (app/services/zoho/http_client.py)   │ │
│  │  v1 REST (form-data)  +  v3 REST (JSON)                      │ │
│  │  auto token refresh · retry · rate-limit backoff             │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                              │                                    │
│                     Zoho Projects API (cloud)                     │
└───────────────────────────────────────────────────────────────────┘
        │
        ├──────────────────────────────────────────────────────────┐
        ▼ (checkpoint read/write on every ainvoke)                 ▼ (cache + rate limit)
┌───────────────────────────┐                    ┌─────────────────────────────────────┐
│      MongoDB Atlas        │                    │           Redis Cloud               │
│  user_tokens              │                    │  cache:project:*  (project lookup)  │
│  chat_sessions            │                    │  cache:user:*     (user lookup)     │
│  checkpoints              │                    │  slot:*           (timelog slots)   │
│  checkpoint_writes        │                    │  rate:*           (rate limiting)   │
└───────────────────────────┘                    └─────────────────────────────────────┘
```

### Key architectural decisions

| Decision | Reason |
|---|---|
| Supervisor + 5 sub-agents | Each sub-agent has a focused role (CRUD) — smaller tool lists reduce LLM confusion and token cost |
| `langchain.agents.create_agent` | Handles the LLM → tool → LLM ReAct loop without manually wiring a state graph |
| AzureChatOpenAI singleton | Stateless, thread-safe — avoids ~30–50 ms reconstruction per request |
| `MongoDBSaver` checkpointer | Persists full conversation history; survives server restarts, scales across instances |
| `EncryptedSerializer` + `FernetCipher` | All checkpoint data (messages, tool outputs) encrypted before hitting MongoDB |
| `contextvars` for `user_id` | Per-coroutine isolation — no race conditions across concurrent users |
| `trim_messages` middleware | Token-aware history trimming using official LangChain API — keeps last `AGENT_MEMORY_WINDOW` messages |
| `ToolRetryMiddleware` | Built-in LangChain retry with exponential backoff — handles Zoho API 429s transparently |
| Per-user rate limit | Redis sorted-set sliding window per `user_id` — multi-pod safe, prevents runaway costs |
| Redis shared cache | Replaces in-memory dicts — all pods share the same project/user/slot cache; survives pod restarts |
| Fuzzy name resolvers | Users speak project/task names naturally — resolvers map fuzzy names to exact Zoho IDs |

---

## 2. Tech Stack

| Technology | Purpose |
|---|---|
| **FastAPI** | Async-native framework — handles HTTP and WebSocket in the same process |
| **Azure OpenAI (GPT-4.x)** | LLM for supervisor routing, sub-agent reasoning, and STT transcript correction |
| **LangChain + LangGraph** | `create_agent` orchestrates each sub-agent's ReAct loop; LangGraph manages state graph internally |
| **MongoDBSaver (LangGraph)** | Persists conversation checkpoints per `thread_id` across restarts |
| **Motor (async MongoDB)** | Non-blocking async client for `user_tokens`, `chat_sessions` |
| **Redis (redis[asyncio])** | Shared cache for project/user/slot lookups + distributed rate limiter — multi-pod safe |
| **httpx** | Async HTTP client — shared singleton for all Zoho API calls |
| **Fernet (cryptography)** | AES-128-CBC + HMAC-SHA256 — encrypts OAuth tokens and all checkpoint data |
| **structlog** | Colored console logs in dev; JSON lines in staging/prod |
| **pydantic-settings** | Type-safe config loading from `.env`; refuses to start on blank/placeholder values |
| **pyttsx3 / SAPI5** | Text-to-speech: SAPI5 on Windows (high quality), pyttsx3 + espeak-ng on Linux |

**Python version:** 3.11 or 3.12 only.

---

## 3. Full Request Cycle

```
User sends: "Log 2 hours to Task Alpha from 10am to 12pm"
                │
                ▼ POST /api/chat (form: message, user_id, chat_id, tenant_id)
                │
        1. RequestTracingMiddleware — assign X-Request-Id, start timer
        2. check_rate_limit(user_id) — Redis sorted-set sliding window per user
        3. get_user_token(user_id) — read from MongoDB, decrypt tokens
           → if not connected: return {action: "connect_required"}
           → if portal_selection_pending: return {action: "connect_required"}
        4. resolve tenant_id + chat_id — fallback to "default" / email in browser context
        5. save_chat_session() — upsert chat_id record in MongoDB, refresh last_active_at
                │
                ▼ agent_chat(user_id, message, chat_id, tenant_id, user_email)
                │
        6. set_user_id(user_id) — store in contextvars (per-coroutine isolation)
        7. set_request_context() — inject [Today is DATE] [Current user's email: X]
        8. thread_id = "{tenant_id}:{chat_id}"
                │
                ▼ try: supervisor.ainvoke({messages: [user_message]}, thread_id=...)
                │       finally: touch_checkpoint_ttl() — always runs, even on crash
                │
        9.  LangGraph loads prior conversation from MongoDB checkpoint (decrypted)
        10. trim_messages_middleware — drops orphaned tool_calls, trims to last 35 messages
        11. Supervisor LLM routes request → calls update_agent_tool("Log 2 hours...")
        12. update_agent receives input with date + email context prepended
        13. Update agent LLM decides: call get_timelogs_for_date (prerequisite check)
        14. tool_retry_middleware wraps execution — 3 retries with backoff on failure
        15. ToolNode executes get_timelogs_for_date → ZohoHttpClient → Zoho API
        16. Result returned to sub-agent LLM
        17. Sub-agent decides: call create_time_log (slot is free)
        18. ToolNode executes create_time_log → Zoho v3 POST
        19. Sub-agent generates reply → Supervisor forwards it unchanged
        20. Checkpoint written back to MongoDB (Fernet-encrypted)
        21. touch_checkpoint_ttl() — refreshes last_modified_at on checkpoint docs
                │
                ▼ reply returned to frontend
        "Done! I've logged 2 hours to Task Alpha from 10:00 AM – 12:00 PM."
```

---

## 4. Agent Architecture

### Supervisor + Sub-Agent Pattern

The system uses a two-level hierarchy:

1. **Supervisor** (`app/agents/supervisor.py`) — receives every user message and routes it to the correct sub-agent based on intent. It never calls Zoho tools directly.

2. **Five sub-agents**, each with its own LLM loop and focused tool set:

| Sub-agent | File | Responsibility |
|---|---|---|
| GET agent | `app/agents/sub_agent/get_agent.py` | Read-only — list, get details, view comments, check status |
| CREATE agent | `app/agents/sub_agent/create_agent.py` | New entities — task, bug, project, task list, time log |
| ADD agent | `app/agents/sub_agent/add_agent.py` | Attach/associate — add comment, link bugs, assign user, add resolution |
| UPDATE agent | `app/agents/sub_agent/update_agent.py` | Modify existing — update status, edit comment, change priority |
| DELETE agent | `app/agents/sub_agent/delete_agent.py` | Remove/unlink — delete task, delete bug, unlink associations |

### Supervisor routing rules

- Routes based on the verb/intent in the user message
- **"add resolution"** always goes to ADD agent, even when status update is also requested
- When user answers a numbered list (e.g. "1" or "the first one"), supervisor re-delegates to the same agent that asked the question
- Supervisor forwards sub-agent replies unchanged — it never rewrites them
- **Anti-splitting:** Never breaks bulk requests (e.g., pasting 10 time entries) into parallel tool calls. Passes massive text blocks intact to sub-agents so they can use native bulk tools.

### Middleware stack

Two middleware functions are registered on the supervisor agent, following the official LangChain 2026 middleware pattern:

| Middleware | Type | What it does |
|---|---|---|
| `trim_messages_middleware` | `@wrap_model_call` | Before each LLM call: drops orphaned AI tool_call messages (prevents 400 errors from broken checkpoints), then applies `langchain_core.messages.trim_messages` with `strategy="last"`, `include_system=True`, `start_on="human"` |
| `tool_retry_middleware` | `ToolRetryMiddleware` | Built-in LangChain middleware — automatically retries failed tool calls up to `TOOL_RETRY_MAX_RETRIES` times with exponential backoff + jitter. Critical for Zoho API rate limits (429s) |

### Why `trim_messages` and not custom slicing?

`trim_messages` from `langchain_core.messages` is the official 2026 LangChain API for history management. It handles `SystemMessage` preservation, `start_on="human"` enforcement, and partial message splitting automatically. The custom window-slicing approach was replaced because it was token-unaware and required manual message boundary management.

The one custom addition on top of `trim_messages` — dropping AI messages with unanswered `tool_calls` — is not covered by the official API and prevents HTTP 400 errors when LangGraph checkpoints contain interrupted tool call sequences.

### Why `ToolRetryMiddleware` and not try/except?

The previous `handle_tool_errors` caught exceptions and returned a `ToolMessage` telling the agent to retry — wasting one full LLM reasoning turn per failure. `ToolRetryMiddleware` retries **before the agent sees the failure**, transparently, with exponential backoff and jitter. No extra LLM call. No extra cost.

### Why middleware — and not something else?

`create_agent` compiles a LangGraph `StateGraph` internally and seals it. The only official interception points are `@wrap_model_call` and `@wrap_tool_call`.

| Approach | Why it does not work here |
|---|---|
| **LangChain Callbacks** | Read-only — cannot modify input messages or replace tool errors with valid results |
| **Build a custom `ToolNode`** | Requires manually wiring the full `StateGraph` — defeats the purpose of `create_agent` |
| **Pre/post-process in `chat()`** | Fires only once on entry; misses inner LLM calls in the ReAct loop |

### Memory and isolation

- **Thread memory** — `thread_id = "{tenant_id}:{chat_id}"` scopes history to one Teams chat. All messages, tool calls, and results are persisted (encrypted) in MongoDB.
- **User isolation** — `contextvars.ContextVar("USER_ID")` stores `user_id` per coroutine. Tools call `get_user_id()` without argument passing.
- **Context forwarding** — date and user email are prepended to every sub-agent input by the supervisor before handing off to the appropriate sub-agent.
- **Conversation window** — `trim_messages_middleware` enforces `AGENT_MEMORY_WINDOW` (default 35) messages per LLM call.

---

## 5. Voice AI Flow

```
Browser / Teams Voice Tab
        │  WebSocket /ws/voice
        ▼
1. Frontend sends {type: "config", user_id, tenant_id, chat_id, voice}
        │
        ▼ Session initialized — WS stays open
        │
2. Browser captures microphone → STT (browser-side Web Speech API)
        │
3. Frontend sends {type: "correct", text: "<raw transcript>"}
        │
        ▼ correct_transcript() — Azure OpenAI LLM call
           System: "Fix STT errors. 'add a new dog' → 'add a new task'"
           Returns corrected text
        │
4. Frontend sends {type: "chat", text: "<corrected transcript>"}
        │
        ▼ handle_chat() — same agent_chat() path as HTTP
           auth check → supervisor → sub-agent → reply
        │
5. TTS pipeline (runs in thread pool via asyncio.to_thread):
   clean_for_speech() — strips markdown, links, symbols
   PyttsxTTS.synthesize() → platform TTS subprocess
     Windows: SAPI5 via win32com (Zira / David voices)
     Linux:   pyttsx3 + espeak-ng
   Returns WAV bytes
        │
6. Frontend receives:
   {type: "reply", text: "...", audio_b64: "<base64 WAV>", audio_mime: "audio/wav"}
        │
7. Browser plays audio via Web Audio API
```

### Voice profiles (`VOICE_PROFILES` in `app/config/settings.py`)

| Profile | Engine | Rate |
|---|---|---|
| `female` | Zira (Windows) / en+f3 (Linux) | 175 wpm |
| `male` | David (Windows) / en+m3 (Linux) | 175 wpm |
| `fast` | Zira/David | 220 wpm |
| `professional` | David/Zira | 155 wpm |
| `warm` | Zira/David | 168 wpm |

---

## 6. OAuth & Token Flow

### First-time Zoho login

```
1.  User opens app inside Microsoft Teams
2.  Teams SDK provides user's email / UPN
3.  Frontend calls GET /auth/zoho/status → {connected: false}
4.  Frontend shows "Connect to Zoho" card
5.  User clicks the button
6.  Frontend opens: GET /auth/zoho/login?teams_user_id=...&teams_tenant_id=...
7.  Backend builds HMAC-signed state, redirects to Zoho consent page
8.  User approves Zoho permissions
9.  Zoho redirects to GET /auth/zoho/callback?code=...&state=...
10. Backend:
      - Validates HMAC signature on state (CSRF protection)
      - Exchanges code for access_token + refresh_token
      - Fetches Zoho user profile + portal list
      - Encrypts both tokens with Fernet, saves to MongoDB
      - Redirects to APP_URL/select-portal (multiple orgs) or APP_URL?connected=true
11. Frontend polling detects connected=true → shows welcome message
```

### Token lifecycle

| Aspect | Detail |
|---|---|
| Access token lifetime | ~1 hour (Zoho default) |
| Refresh token | Does not expire unless user revokes |
| Auto-refresh trigger | `TOKEN_REFRESH_THRESHOLD` seconds before expiry |
| On refresh failure | `TokenRefreshError` raised; frontend prompted to reconnect |

### Token resolution per request (`get_valid_token`)

```
get_valid_token(user_id)
        │
        ├─► Step 1: In-memory cache
        │     token_cache[user_id] → (access_token, expires_at)
        │     If valid and not near expiry → return immediately (no DB, no network)
        │
        ├─► Step 2: Cache miss → MongoDB
        │     get_user_token(user_id) → decrypt access_token + refresh_token
        │     If still fresh → warm cache, return
        │
        └─► Step 3: Expired → acquire per-user lock
              Double-check DB (another coroutine may have refreshed already)
              POST /oauth/v2/token → Zoho returns new access_token
              save_to_mongodb (encrypted) + warm cache
              return new token
```

**Why the per-user lock?** Without it, concurrent requests for the same user all detect an expired token and all POST to Zoho's token endpoint simultaneously — only the first succeeds. Double-checked locking ensures exactly one refresh per user.

---

## 7. Caching — All Layers End to End

All caching exists for **response speed**. The latency problem without caching:

| Without cache | Latency added per message |
|---|---|
| Token cache miss → MongoDB read on every tool call | +10–50 ms × 5 calls = **+50–250 ms** |
| Project cache miss → 1–3 paginated Zoho API calls | +200–1,500 ms per tool call |
| Slot cache absent → Zoho propagation delay causes double-booking | correctness failure |

### Layer 1 — In-memory access token cache (`app/auth/token_manager.py`)

```python
token_cache: dict[str, tuple[str, float]] = {}
# user_id → (access_token_plaintext, expires_at_float)
```

Saves one MongoDB read + possible Zoho refresh call per request.

### Layer 2 — Project / user name resolution cache (`app/utils/cache.py`)

```
Redis key: cache:project:(portal_id, normalized_name)   → JSON project object   TTL: CACHE_TTL_SECONDS
Redis key: cache:user:(portal_id, email)                → JSON user object       TTL: CACHE_TTL_SECONDS
```

Key includes `portal_id` to prevent cross-org data leakage in multi-tenant setup. Saves 1–3 paginated Zoho API calls per resolution. TTL is set via Redis `SETEX` — entries auto-expire. Shared across all backend pods — a cache warm on Pod A is immediately visible to Pod B.

### Layer 3 — Timelog slot cache (`app/utils/cache.py`)

```
Redis key: slot:{owner_email}:{date_string}   → JSON list of booked slots   TTL: CACHE_TTL_SECONDS
```

Zoho has a propagation delay — a freshly created timelog may not appear in the next `GET /logs/` for a few seconds. This cache stores newly booked slots immediately to prevent double-booking within the same session. Because it lives in Redis (not process memory), it also survives pod restarts and is consistent across all backend pods.

### Layer 4 — Task layout cache (`app/tools/tasks/update_task_status.py`)

```python
TASKLAYOUT_CACHE = {}
# project_id → [{"name": str, "id": str}, ...]
```

In-process dict (not Redis). Caches Zoho task status layouts per project. Status layouts almost never change, so this lives for the application lifetime (cleared only on pod restart). Avoids repeated `/tasklayouts` API calls on every status update. Not shared across pods — each pod warms its own copy on first use.

---

## 8. MongoDB — What Is Stored, How, and What Is Encrypted

### Why checkpoints are stored in MongoDB, not RAM

RAM is fast but volatile. MongoDB checkpoints give:

| Scenario | RAM only | MongoDB |
|---|---|---|
| Server restart | All conversation history lost | Resumes exactly where left off |
| User returns after 1hr | Context gone | Full history available |
| Multiple server instances | User hits different server, loses context | All servers share same DB |
| Agent crashes mid-tool-call | Lost | LangGraph replays from last good state |

RAM burden is bounded by `trim_messages_middleware` — only the last 35 messages are sent to the LLM per call. MongoDB TTL auto-deletes sessions after 1hr of inactivity.

### Collections

#### `user_tokens`

One document per user. Stores Zoho OAuth credentials — **never auto-expires** (auth data, not session data).

| Field | Encrypted | Notes |
|---|---|---|
| `teams_user_id` | No | Lowercased Teams UPN / email — primary key |
| `teams_tenant_id` | No | Entra tenant GUID |
| `teams_oid` | No | Entra Object ID — only populated in real Teams bot context (empty in browser) |
| `zoho_user_id` | No | Zoho ZUID — populated from `/userinfo` if scope returns it |
| `zoho_org_id` | No | Zoho portal numeric ID (used for v3 API) |
| `email` | No | User's email from Zoho profile |
| `access_token` | **Yes** | Fernet-encrypted before insert |
| `refresh_token` | **Yes** | Fernet-encrypted before insert |
| `expires_at` | No | Unix timestamp |
| `api_domain` | No | Per-user Zoho region (e.g. `zohoapis.in`) |
| `portals` | No | List of available orgs (cleared after selection) |
| `portal_selection_pending` | No | `true` until org is chosen |

#### `chat_sessions`

One document per chat thread. Maps `chat_id → user_id + tenant_id`.

| Field | Notes |
|---|---|
| `chat_id` | Teams Chat ID — unique, primary key |
| `tenant_id` | Entra tenant GUID (or `"default"` in browser context) |
| `user_id` | Lowercased Teams user |
| `last_active_at` | Refreshed on every message — drives TTL |

#### `checkpoints` and `checkpoint_writes`

Managed by **LangGraph `MongoDBSaver`**. Contains the full conversation history per `thread_id = "{tenant_id}:{chat_id}"`.

- **All content encrypted** via `EncryptedSerializer` + `FernetCipher` (AES-128-CBC + HMAC-SHA256)
- TTL on `last_modified_at` — refreshed by `touch_checkpoint_ttl()` after every message

### When data is deleted

| Trigger | `chat_sessions` | `checkpoints` + `checkpoint_writes` | `user_tokens` |
|---|---|---|---|
| **1hr inactivity** | Auto-deleted (TTL on `last_active_at`) | Auto-deleted (TTL on `last_modified_at`) | Kept — auth data |
| **New chat** | Deleted (`delete_chat_session`) | Deleted (`adelete_thread`) | — |
| **Disconnect** | Deleted (`delete_user_sessions`) | Deleted (`adelete_thread` for all threads) | Deleted (`delete_user_token`) |

`touch_checkpoint_ttl()` runs in a `finally` block in `agent_runner.py` — it always executes, even when the agent crashes, ensuring `last_modified_at` is always written and the TTL clock always resets correctly.

### Indexes created at startup (`app/db/indexes.py`)

| Collection | Index | Type | Purpose |
|---|---|---|---|
| `user_tokens` | `teams_user_id` | Unique | One record per user, fast lookup |
| `chat_sessions` | `chat_id` | Unique | One session per Teams chat |
| `chat_sessions` | `(tenant_id, user_id)` | Compound | Fast lookup of all sessions for a user within a tenant |
| `chat_sessions` | `last_active_at` | TTL (sparse) | Auto-delete idle sessions |
| `checkpoints` | `last_modified_at` | TTL (sparse) | Auto-delete idle agent state |
| `checkpoint_writes` | `last_modified_at` | TTL (sparse) | Auto-delete idle write records |

### Encryption detail

```
Fernet (cryptography library) = AES-128-CBC + HMAC-SHA256

Two encryption contexts, one key (ENCRYPTION_KEY):

  1. OAuth tokens (access_token, refresh_token):
       string → Fernet.encrypt(bytes) → base64 string → MongoDB
       Handled by encrypt() / decrypt() in app/utils/crypto.py

  2. LangGraph checkpoints (all conversation data):
       LangGraph serializes checkpoint → msgpack bytes
       FernetCipher.encrypt(bytes) → ("fernet", ciphertext_bytes)
       EncryptedSerializer stores type prefix + ciphertext
       On read: FernetCipher.decrypt() → msgpack → checkpoint
```

---

## 9. Multi-Tenant & Multi-User Architecture

### How multi-tenancy works

Every request carries three identity fields:

| Field | Source | Purpose |
|---|---|---|
| `user_id` | Teams UPN / email | Identifies the individual user |
| `tenant_id` | Teams org GUID | Identifies the organisation |
| `chat_id` | Teams Chat ID | Identifies the specific conversation thread |

These combine into `thread_id = "{tenant_id}:{chat_id}"` — scoping all agent memory to one org's chat. Users from different tenants with the same `chat_id` will never share a thread.

### Per-request user isolation

```python
# app/utils/request_context.py
USER_ID: contextvars.ContextVar[str] = contextvars.ContextVar("USER_ID")
```

Each async request gets its own `USER_ID` context variable. Tools call `get_user_id()` to identify the current user without passing arguments through the call stack. No shared state between concurrent users.
