'''
Application settings and constants (Pydantic-based env config + static mappings)
Used across app for API configs, auth, logging, TTS, and runtime environment control
'''
from enum import StrEnum
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

#Environment Types
class Environment(StrEnum):
    LOCAL   = "local"
    DEV     = "dev"
    STAGING = "staging"
    PROD    = "prod"

# Zoho Projects API domain per region — derive correct endpoint from api domain returned by Zoho
ZOHO_PROJECTS_DOMAIN_MAP: dict[str, str] = {
    "zohoapis.in":     "projectsapi.zoho.in",
    "zohoapis.com":    "projectsapi.zoho.com",
    "zohoapis.eu":     "projectsapi.zoho.eu",
    "zohoapis.com.cn": "projectsapi.zoho.com.cn",
    "zohoapis.com.au": "projectsapi.zoho.com.au",
}

# TTS voice profiles — keywords match Windows SAPI5 voice descriptions
VOICE_PROFILES: dict = {
    "female":       {"keywords": ["zira", "female"], "rate": 175, "sapi_rate":  0},
    "male":         {"keywords": ["david", "male"],  "rate": 175, "sapi_rate":  0},
    "fast":         {"keywords": ["zira", "david"],  "rate": 220, "sapi_rate":  3},
    "professional": {"keywords": ["david", "zira"],  "rate": 155, "sapi_rate": -2},
    "warm":         {"keywords": ["zira", "david"],  "rate": 168, "sapi_rate": -1},
}

# Linux espeak-ng voice IDs — SAPI5 keyword matching does not work on Linux
LINUX_VOICE_MAP: dict = {
    "female":       "en+f3",
    "male":         "en+m3",
    "fast":         "en+f3",
    "professional": "en+m3",
    "warm":         "en+f3",
}

# Zoho OAuth scopes required for full project management access permissions.
ZOHO_SCOPES = [
    "ZohoProjects.portals.ALL",
    "ZohoProjects.projects.ALL",
    "ZohoProjects.milestones.ALL",
    "ZohoProjects.tasklists.ALL",
    "ZohoProjects.tasks.ALL",
    "ZohoProjects.timesheets.ALL",
    "ZohoProjects.bugs.ALL",
    "ZohoProjects.users.ALL",
    "AaaServer.profile.READ",
]
#Application Settings (Loaded from environment file)
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Azure OpenAI ──────────────────────────────────────────────────────────
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_API_KEY: str
    AZURE_OPENAI_DEPLOYMENT: str
    AZURE_OPENAI_API_VERSION: str

    # ── Zoho OAuth ────────────────────────────────────────────────────────────
    ZOHO_CLIENT_ID: str
    ZOHO_CLIENT_SECRET: str
    ZOHO_REDIRECT_URI: str
    ZOHO_TOKEN_URL: str
    ZOHO_AUTH_URL: str
    ZOHO_USERINFO_URL: str
    ZOHO_PROJECTS_API_DOMAIN: str   # e.g. projectsapi.zoho.in
    ZOHO_API_DOMAIN: str            # e.g. https://www.zohoapis.in

    # ── MongoDB ───────────────────────────────────────────────────────────────
    MONGODB_URI: str

    # ── Encryption ────────────────────────────────────────────────────────────
    ENCRYPTION_KEY: str             # Fernet key — encrypts tokens stored in MongoDB.

    # ── App ───────────────────────────────────────────────────────────────────
    APP_URL: str                    # frontend URL — used for OAuth redirect-back
    APP_HOST: str
    APP_PORT: int
    REDIS_URL: str                  
    REDIS_PORT: int
    REDIS_KEY: str
    REDIS_USERNAME: str
    ENVIRONMENT: Environment
    LOG_LEVEL: str
    LOG_RENDERER: str               # console | json — set console for local, json for prod/staging
    CORS_ORIGINS: str
    UVICORN_RELOAD: bool            # true for local/dev, false for staging/prod — set in .env

    # ── Agent / LLM tuning ────────────────────────────────────────────────────
    AGENT_TEMPERATURE: float
    AGENT_MEMORY_WINDOW: int        # number of conversation turn-pairs kept in history
    AGENT_MAX_ITERATIONS: int       # max tool calls per agent run
    AGENT_MAX_TOKENS: int           # max tokens sent to LLM per turn (trim_messages cap)
    AGENT_TIMEOUT: int              # seconds before agent invocation is cancelled
    AGENT_LLM_CONCURRENCY: int      # max parallel Azure OpenAI calls across all users
    MAX_INPUT_LEN: int              # max characters accepted per user message
    TOOL_RETRY_MAX_RETRIES: int     # max retries on tool call failure (ToolRetryMiddleware)
    TOOL_RETRY_BACKOFF_FACTOR: float  # exponential backoff multiplier between retries
    TOOL_RETRY_INITIAL_DELAY: float   # initial delay in seconds before first retry
    TOOL_RETRY_JITTER: bool           # add randomness to retry delays to avoid thundering herd

    # ── Zoho HTTP client timeouts ─────────────────────────────────────────────
    ZOHO_TIMEOUT_CONNECT: float     # seconds to establish TCP connection
    ZOHO_TIMEOUT_READ: float        # seconds to wait for Zoho response
    ZOHO_TIMEOUT_WRITE: float       # seconds to send request body
    ZOHO_TIMEOUT_POOL: float        # seconds to wait for a free connection in pool

    # ── OAuth settings ────────────────────────────────────────────────────────
    OAUTH_HTTP_TIMEOUT: float       # timeout for auth HTTP calls (token exchange, userinfo)
    OAUTH_STATE_MAX_AGE: int        # seconds OAuth state is valid — user must consent within this window
    OAUTH_MAX_RETRIES: int          # max retries on network errors /  for token endpoints
    ZOHO_TOKEN_DEFAULT_EXPIRY: int  # fallback expires_in (seconds) if Zoho omits it in response
    TOKEN_EXPIRY_BUFFER: int        # seconds before expiry to treat token as expired (prevents edge-case failures)
    TOKEN_REFRESH_THRESHOLD: int    # seconds before expiry to proactively trigger a refresh

    # ── Data retention ────────────────────────────────────────────────────────
    CHAT_HISTORY_TTL_SECONDS: int   # seconds before idle chat sessions are auto-deleted by MongoDB TTL

    # ── Tool helper tuning ( @tool functions) ───────────────────────────
    CACHE_TTL_SECONDS: int          # seconds before project/user in-memory cache entries expire
    RESOLVER_CACHE_MAX: int         # max entries per cache dict before oldest are evicted
    RESOLVER_MAX_PAGES: int         # max pages to scan when resolving project or task names
    RESOLVER_PAGE_SIZE: int         # results per page when fetching projects or tasks

    # ── Resolver matching thresholds ──────────────────────────────────────────
    RESOLVER_MIN_SCORE: int         # minimum score to consider any entity a match
    RESOLVER_STRONG_MATCH: int      # score required for tasklist candidates and user scoring
    RESOLVER_AMBIGUITY_GAP: int     # score gap between top-2 results below which result is ambiguous

    # ── WebSocket ─────────────────────────────────────────────────────────────
    WS_RECEIVE_TIMEOUT: int         # seconds before sending a ping to keep connection alive
    # ── Office Hours (used for timelog free-slot calculation) ────────────────
    OFFICE_START_TIME: str          # office start in HH:MM 24hr format 
    OFFICE_END_TIME: str            # office end   in HH:MM 24hr format
    # ── Rate limiting ─────────────────────────────────────────────────────────
    RATE_LIMIT_MAX_CALLS: int       # max requests per user per window
    RATE_LIMIT_WINDOW_SECS: int     # sliding window size in seconds

    # ── Defaults ─────────────────────────────────────────────────────────────
    DEFAULT_USER_ID: str            # fallback user ID for local testing only
    DEFAULT_VOICE: str              # default TTS voice profile (female | male | fast | professional)

    # ── Startup validation ────────────────────────────────────────────────────
    @model_validator(mode="after")
    def reject_placeholders(self) -> "Settings":
        # Refuse to start if any critical field is blank or still a placeholder
        CHECK = {
            "AZURE_OPENAI_ENDPOINT":    self.AZURE_OPENAI_ENDPOINT,
            "AZURE_OPENAI_API_KEY":     self.AZURE_OPENAI_API_KEY,
            "AZURE_OPENAI_DEPLOYMENT":  self.AZURE_OPENAI_DEPLOYMENT,
            "ZOHO_CLIENT_ID":           self.ZOHO_CLIENT_ID,
            "ZOHO_CLIENT_SECRET":       self.ZOHO_CLIENT_SECRET,
            "ZOHO_REDIRECT_URI":        self.ZOHO_REDIRECT_URI,
            "MONGODB_URI":              self.MONGODB_URI,
            "ENCRYPTION_KEY":           self.ENCRYPTION_KEY,
            "APP_URL":                  self.APP_URL,
        }
        BAD = ("your-", "your_", "<", "changeme", "example.com")  # Common placeholder patterns (invalid values like "user-key", "changeme"..)
        errors = [
            f"  {k} — {'not set' if not str(v).strip() else f'placeholder: {v!r}'}"
            for k, v in CHECK.items()
            if not str(v).strip() or any(m in str(v).lower() for m in BAD)
        ]
        if errors: # Build error list for missing or placeholder values
            if self.ENVIRONMENT in (Environment.LOCAL, Environment.DEV):
                try:
                    import warnings
                    warnings.warn("Missing/placeholder config detected:\n" + "\n".join(errors))
                except Exception:
                    pass
            else:
                raise ValueError("\n\nFix your .env:\n" + "\n".join(errors))
        return self

SETTINGS = Settings()
