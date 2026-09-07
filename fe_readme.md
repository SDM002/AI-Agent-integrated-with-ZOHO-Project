# Zoho PM Agent — Frontend

AI-powered voice and text chat interface for Zoho Projects, built with Next.js 16 (App Router) for Microsoft Teams deployment.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Repository Structure](#3-repository-structure)
4. [Tech Stack](#4-tech-stack)
5. [Environment Variables](#5-environment-variables)
6. [Installation & Running](#6-installation--running)
7. [Pages & Routes](#7-pages--routes)
8. [Proxy Layer](#8-proxy-layer)
9. [Zoho Connection Flow](#9-zoho-connection-flow)
10. [Chat Interface Behavior](#10-chat-interface-behavior)
11. [Voice Chat (WebSocket)](#11-voice-chat-websocket)
12. [Multi-Tenant Identity](#12-multi-tenant-identity)
13. [DevTunnel Setup](#13-devtunnel-setup)
14. [Common Errors](#14-common-errors)

---

## 1. Overview

This is the **Next.js 16** frontend for the Zoho PM Agent. It provides:

- A full-featured **text and voice chat interface** for interacting with Zoho Projects through an AI agent, including rich Markdown rendering for tables and formatted data
- **Microsoft Teams integration** via the Teams JS SDK — automatically detects the logged-in Teams user
- A **Zoho OAuth connection flow** with portal selection for multi-org users
- A **WebSocket voice pipeline**: microphone capture → speech-to-text → AI agent → TTS audio playback
- A **server-side proxy layer** that forwards all HTTP calls to the FastAPI backend, eliminating CORS issues
- **Dark/light theme** with animated orb UI, smooth transitions, and responsive design

---

## 2. Architecture

```
Microsoft Teams (iframe)  /  Browser
         │
         ▼
Next.js Frontend  (<frontend-port>)
  ├── /                         → Main chat interface
  ├── /select-portal            → Portal picker after Zoho OAuth
  ├── /api/[...path]            → Server-side proxy → FastAPI /api/*
  ├── /auth/[...path]           → Server-side proxy → FastAPI /auth/*
  └── /ws/[...path]             → Server-side proxy → FastAPI /ws/* (HTTP upgrade not supported)
         │  (server-side, uses BACKEND_URL)
         ▼
FastAPI Backend  (<backend-port>)
  ├── /api/chat                 ← HTTP text chat
  ├── /auth/zoho/*              ← OAuth login, callback, status, disconnect
  └── /ws/voice                 ← WebSocket voice channel (browser connects directly)
```

**Single env var — `BACKEND_URL`:**

`BACKEND_URL` is the only required environment variable. It is server-side only (never sent to the browser directly).

- All HTTP requests from the browser go through the Next.js server-side proxy, which reads `BACKEND_URL`.
- WebSocket connections cannot be proxied through Next.js App Router. Instead, the browser calls `GET /api/deployment/ws-url` (a Pages Router API route), which reads `BACKEND_URL` server-side, converts `http` → `ws` / `https` → `wss`, and returns the WebSocket URL to the browser. The browser then connects directly to that URL.

This means `BACKEND_URL` must be a URL reachable from both the Next.js server process (for HTTP proxy) **and** from the end-user's browser (for WebSocket). In local development both are `localhost`, so one value works. For DevTunnel or production, see Section 13.

---

## 3. Repository Structure

```
af-fe-zoho-voice-agents/
├── src/
│   ├── app/
│   │   ├── layout.js                   # Root layout — fonts, metadata
│   │   ├── globals.css                 # Global styles
│   │   ├── page.js                     # Main chat page — orchestrates all hooks
│   │   ├── select-portal/
│   │   │   └── page.js                 # Portal picker after OAuth (multi-org accounts)
│   │   ├── api/[...path]/
│   │   │   └── route.js                # Catch-all proxy → FastAPI /api/*
│   │   ├── auth/[...path]/
│   │   │   └── route.js                # Catch-all proxy → FastAPI /auth/*
│   │   └── ws/[...path]/
│   │       └── route.js                # Catch-all proxy → FastAPI /ws/* (HTTP only)
│   ├── hooks/
│   │   ├── useZohoAuth.js              # Teams SDK init, Zoho status polling, connect/disconnect
│   │   ├── useWebSocket.js             # WS connect/disconnect, message dispatch
│   │   ├── useWsBaseUrl.js             # Fetches WS base URL from /api/deployment/ws-url on mount
│   │   ├── useAudioPlayer.js           # Bot TTS audio playback, echo prevention
│   │   └── useSpeechRecognition.js     # webkitSpeechRecognition lifecycle, dedup, flush
│   ├── lib/
│   │   ├── proxy.js                    # Shared proxy utility used by all route handlers
│   │   └── config.js                  # Exports BACKEND_URL, FETCH_TIMEOUT_MS, FETCH_RETRY_DELAY_MS (reads window.__RUNTIME_ENV__ or process.env)
│   ├── services/
│   │   ├── api.js                      # wsUrl() helper (unused — see useWsBaseUrl.js)
│   │   └── wsProxy.js                  # getWsUrl() helper (unused — see useWsBaseUrl.js)
│   ├── pages/api/deployment/
│   │   └── ws-url.js                   # Pages Router API — reads BACKEND_URL server-side, returns ws(s):// URL to browser
│   └── components/
│       ├── Header.js                   # Top bar — Zoho status, voice selector, theme toggle
│       ├── ChatMessages.js             # Message bubbles, connect card, disconnect banner
│       ├── InputBar.js                 # Text input + mic button + transcript preview
│       ├── EnhancedAIOrb.js           # Animated AI orb (idle/listening/processing/speaking)
│       ├── EnhancedBackground.js       # Animated grid background
│       ├── ChatPanel.js               # Chat panel wrapper
│       ├── VoiceMode.js               # Voice mode UI
│       └── ui/                        # shadcn/ui component library
├── public/                            # Static assets
├── next.config.mjs                    # Next.js config
└── package.json
```

---

## 4. Tech Stack

| Technology | Version | Purpose |
|---|---|---|
| **Next.js (App Router)** | 16.2.6 | File-based routing, server-side proxy route handlers |
| **React** | 19.2.4 | UI framework |
| **Motion** | 12.38.0 | Animations for orb, cards, message bubbles |
| **Microsoft Teams JS SDK** | latest | Reads logged-in Teams user email for identity |
| **Web Speech API** | browser-native | Speech-to-text (microphone capture) |
| **WebSocket** | browser-native | Real-time bidirectional voice channel to FastAPI |
| **Tailwind CSS** | v4 | Utility-first styling |
| **shadcn/ui + Radix UI** | — | Accessible component primitives |
| **Custom Markdown parser** | — | Hand-written block + inline parser in `ChatMessages.js` — handles tables, headers, bold, lists, inline code |

---

## 5. Environment Variables

Create `.env.local` in the project root:

```env
# Required — used by the Next.js proxy AND the ws-url API route (both server-side)
BACKEND_URL=<your-backend-url>

# Optional — override fetch timeout and retry delay (milliseconds)
FETCH_TIMEOUT_MS=30000
FETCH_RETRY_DELAY_MS=1000
```

> `BACKEND_URL` is server-side only — it is never directly exposed to the browser.
> The browser receives the WebSocket URL by calling `GET /api/deployment/ws-url`, which converts `BACKEND_URL` to a `ws://` / `wss://` URL server-side and returns it. So `BACKEND_URL` must be reachable from both the Next.js server process (HTTP proxy) and from the user's browser (WebSocket). For DevTunnel constraints, see Section 13.

---

## 6. Installation & Running

### Prerequisites

- Node.js 22+
- FastAPI backend running on port 8000
- MongoDB running (the backend requires it)

### Setup

```bash
npm install
# Create .env.local and set BACKEND_URL (see Section 5)
```

### Development

```bash
npm run dev
```

Opens at `http://<host>:<frontend-port>`.

### Production build

```bash
npm run build
npm start
```

> The `prebuild` script automatically deletes `.next/` before every build to avoid stale cache issues on Windows.

---

## 7. Pages & Routes

### `/` — Main Chat Page (`src/app/page.js`)

The primary interface. Wires together all hooks and renders:

- **Header bar** — Zoho connection status, voice selector, theme toggle, new chat button
- **Chat message area** — scrollable list of user and bot messages with animated bubbles, featuring full markdown rendering for tables, lists, and bold text
- **Animated orb** — pulsing circle reflecting voice state (`idle` / `listening` / `processing` / `speaking`)
- **Text input** — sends via `POST /api/chat` (text mode) or WebSocket `chat` message (voice mode)
- **Mic button** — toggles voice mode and starts/stops WebSocket + speech recognition
- **Zoho connect card** — shown when the user is not connected; contains the OAuth login button

**Key state refs (survive re-renders without triggering effect loops):**

| Ref | Purpose |
|---|---|
| `zohoStatusRef` | Mirrors `zohoStatus` state — used in callbacks to avoid stale closures |
| `connectCardShownRef` | Guard — connect card shown at most once per session |
| `wsRef` | WebSocket instance |
| `micOnRef` | Microphone toggle state |
| `transcriptRef` | Current in-progress voice transcript |

---

### `/select-portal` — Portal Picker (`src/app/select-portal/page.js`)

Shown after Zoho OAuth when the user has multiple Zoho portals. The user picks which portal to use.

- Fetches portal list from `GET /auth/zoho/portals?teams_user_id=<id>`
- On selection: calls `POST /auth/zoho/select-portal` to persist the choice
- **Auto-close countdown:** 3-second countdown after successful selection, then `window.close()`
- The main tab detects connection via status polling and shows a welcome message

---

## 8. Proxy Layer

All HTTP traffic between the browser and backend flows through Next.js server-side route handlers. The proxy is implemented in two files:

**`src/lib/proxy.js`** — shared utility used by all route handlers:
- Reads `BACKEND_URL` from server-side env
- Forwards the request method, headers, and body verbatim
- Sets `host` header to the backend host
- Handles timeouts (120 s) and unreachable backend gracefully

**Route handlers** — catch-all handlers in `src/app/`:

| Route | File | Forwards to |
|---|---|---|
| `/api/*` | `src/app/api/[...path]/route.js` | `<BACKEND_URL>/api/*` |
| `/auth/*` | `src/app/auth/[...path]/route.js` | `<BACKEND_URL>/auth/*` |
| `/ws/*` | `src/app/ws/[...path]/route.js` | `<BACKEND_URL>/ws/*` (HTTP only) |

All HTTP methods (GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS) are exported from each handler.

**Why not `next.config.mjs` rewrites?** Next.js rewrites run client-side (or as edge redirects) and don't hide the target URL. Route handlers run fully server-side, keep `BACKEND_URL` secret, and give full control over headers and error handling.

---

## 9. Zoho Connection Flow

```
1. Page loads → Teams SDK reads user email (or generates guest_<id> for browser sessions)
2. Frontend polls GET /auth/zoho/status?teams_user_id=<email> every 3 seconds
3. If not connected → show "Connect to Zoho" card (shown at most once — guarded by connectCardShownRef)
4. User clicks "Connect to Zoho"
5. Frontend opens the OAuth URL in a new window (Teams iframe blocks external redirects)
6. User approves Zoho permissions
7. Zoho redirects → backend OAuth callback → backend redirects to:
     /select-portal  (if user has multiple portals)
     /?connected=true  (if only one portal, auto-selected)
8. select-portal: user picks their portal → backend persists choice → 3-second countdown → window.close()
9. Frontend polling detects status → connected → removes login card → shows welcome message
```

**Disconnect:**
- User clicks disconnect in the header
- Frontend calls `DELETE /auth/zoho/disconnect?teams_user_id=<id>`
- Local state resets, `connectCardShownRef` is cleared so the login card can appear again

---

## 10. Chat Interface Behavior

### Text chat

Sent via `POST /api/chat` as `multipart/form-data`:

| Field | Value |
|---|---|
| `message` | User's text |
| `user_id` | Teams user email |
| `chat_id` | Teams chat ID (or user_id for web sessions) |
| `tenant_id` | Teams tenant GUID |
| `include_audio` | `false` for text mode |

The backend returns `{ reply, audio_base64? }`. Text replies render as bot messages.

### Voice chat

When voice mode is active, the text input submits via WebSocket `chat` message instead of HTTP POST.

### Zoho connection required

If the backend returns `action: "connect_required"` (HTTP response or WebSocket message), the connect card is shown. The `connectCardShownRef` guard ensures it is never shown twice in the same session.

---

## 11. Voice Chat (WebSocket + WebKit STT)

Voice input uses **browser `webkitSpeechRecognition`** — no raw audio is sent to the backend. Only the corrected text transcript travels over the WebSocket connection.

The WebSocket connects directly from the browser to `NEXT_PUBLIC_BACKEND_URL/ws/voice`. Next.js App Router route handlers do not support WebSocket upgrades, so the proxy route at `/ws/[...path]` handles only HTTP (e.g., REST calls to `/ws/*`).

**Echo prevention:** While backend TTS audio is playing, all STT results are discarded to prevent the mic from picking up the bot's own voice.

**Session auto-restart:** `webkitSpeechRecognition` has a ~60s browser limit. The hook auto-restarts every 55 seconds to handle long pauses.

**Esc key:** Clears the input and cancels the current transcript.

**No auto-reconnect:** If the WebSocket connection drops mid-session (network blip, backend restart), it does not automatically reconnect. The user must reload the page or re-click the mic button to re-establish the connection.

### Frontend → Backend messages

| Type | When sent | Fields |
|---|---|---|
| `config` | On WebSocket connect | `voice`, `user_id`, `chat_id`, `tenant_id` |
| `correct` | After mic stops | `text` (raw STT transcript for GPT correction) |
| `chat` | User submits voice/text | `text` (corrected transcript) |
| `interrupt` | User taps orb while bot speaks | — |
| `ping` | Keep-alive | — |

### Backend → Frontend messages

| Type | When sent | Fields |
|---|---|---|
| `status` | State change | `value`: `listening` / `processing` / `speaking` |
| `transcript_corrected` | After STT correction | `text` |
| `reply` | Agent response | `text`, `audio_b64` (WAV), `audio_mime` |
| `connect_required` | No Zoho token | `text` |
| `interrupted` | Interrupt acknowledged | — |
| `pong` | Ping response | — |

### Orb states

| State | Visual |
|---|---|
| `idle` | Slow pulse, muted color |
| `listening` | Bright pulse, active color |
| `processing` | Spinning animation |
| `speaking` | Animated wave |

---

## 12. Multi-Tenant Identity

The frontend determines the current user via:

1. **Microsoft Teams SDK** — reads `ctx.user.loginHint` or `ctx.user.userPrincipalName` (the Teams/Entra email)
2. **Browser fallback** — generates a `guest_<random>` ID stored in `localStorage` for non-Teams sessions

The user ID is sent with every request (`user_id` form field / WebSocket `config` message). The backend uses it to look up the correct Zoho OAuth tokens and portal from MongoDB — ensuring each user always hits their own Zoho organization.

---

## 13. DevTunnel Setup

DevTunnel is used to expose both the frontend (port 3000) and backend (port 8000) to the internet so Microsoft Teams can load the app.

### The DevTunnel wall problem

DevTunnel URLs have a **browser warning wall** — a page that blocks automated (non-browser) HTTP requests with an HTML warning, causing `ECONNRESET` errors on the server-side proxy.

`BACKEND_URL` is used by both the server-side HTTP proxy and the `ws-url` API route. When `BACKEND_URL` points to the DevTunnel URL, the server-side proxy hits the warning wall and breaks. When it points to the direct backend address, the HTTP proxy works, but the `ws-url` route returns a `ws://` URL that the browser (running inside Teams) cannot reach remotely.

### Recommended `.env.local` for DevTunnel development

For local testing where the browser and the server run on the same machine (regular browser, not Teams):

```env
BACKEND_URL=<direct-backend-address>
```

For testing inside Microsoft Teams via DevTunnel, the WebSocket target must be publicly reachable. Set `BACKEND_URL` to the DevTunnel backend URL — accept the warning wall once in the browser to unblock it, then the WebSocket connection will work:

```env
BACKEND_URL=<devtunnel-backend-url>
```

### Teams manifest

Set the `contentUrl` in `manifest.json` to the frontend DevTunnel URL:

```json
"contentUrl": "<devtunnel-frontend-url>"
```

After changing the tunnel URL: update `manifest.json`, re-zip the manifest folder, and re-upload to Teams Admin.

---

## 14. Common Errors

| Error | Cause | Fix |
|---|---|---|
| `Failed to proxy ... Error: socket hang up` | `BACKEND_URL` points to DevTunnel URL, hitting the warning wall | Set `BACKEND_URL` to the direct backend address for local dev; accept the DevTunnel warning page in browser first if using tunnel URL |
| `BACKEND_URL is not configured` | Missing or empty `BACKEND_URL` in `.env.local` | Add `BACKEND_URL=<your-backend-url>` to `.env.local` |
| WebSocket fails to connect | `/api/deployment/ws-url` returned empty or backend not running | Check `BACKEND_URL` in `.env.local` and ensure the backend is running |
| WebSocket URL unreachable in Teams | `BACKEND_URL` set to a direct/local address but browser runs inside Teams (remote) | Set `BACKEND_URL` to the publicly reachable backend URL — the WS URL is derived server-side from `BACKEND_URL` |
| Login card appears twice | Race between polling and action handler | Fixed via `connectCardShownRef` guard |
| Login card not removed after OAuth | Polling did not detect transition | Verify backend `/auth/zoho/status` returns `connected: true` after callback |
| Teams SDK not initializing | App not running inside Teams | Expected — browser sessions fall back to `guest_<id>` automatically |
| Blank page in Teams | DevTunnel URL changed | Update `contentUrl` in `manifest.json`, re-zip, re-upload |
| `Module not found` after adding hook | Import path wrong | All hooks live in `src/hooks/` — import as `@/hooks/<name>` |
| Build fails on Windows | `.next/` locked by previous process | `npm run clean` deletes `.next/` before build automatically |

---

## 15. Production Readiness — STT Risk & Recommendation

**The voice pipeline is not production-ready.** Voice input uses `window.webkitSpeechRecognition` (browser Web Speech API). Raw audio is sent to a Google-operated cloud service managed entirely by the browser — outside our infrastructure and any enterprise contract. The backend only receives the final text transcript. This creates a compliance gap.

**Risks if shipped to enterprise production:**
- No enterprise DPA or SLA for the STT processing
- Cannot answer GDPR / DPDP data-handling questions with confidence
- Chrome-only, subject to browser session limits, no offline fallback
- Internal audit has flagged this as high severity

### Azure-native replacement options

| Option | Compliance | Estimated cost (200 employees, ~45k min/month) |
|---|---|---|
| **Azure Speech-to-Text** | Enterprise SLA, Microsoft DPA | ~$765/month (~₹63,500) |
| **Whisper via Azure OpenAI** | Azure-native billing | ~$270/month (~₹22,400) |
| **Self-hosted Whisper (Azure GPU)** | Audio never leaves our subscription | ~₹21,000–25,000/month (infra) |

### Recommendation

- **Short-term:** Replace `webkitSpeechRecognition` with **Azure Speech-to-Text** for immediate enterprise compliance.
- **Medium-term:** Migrate to **Whisper via Azure OpenAI** to reduce per-minute cost.
- **Long-term:** Run **self-hosted Whisper** as primary STT with Azure Speech-to-Text as fallback.

Until one of the above is implemented, use `POST /api/chat` (text mode) for production and treat voice as a demo-only feature.
