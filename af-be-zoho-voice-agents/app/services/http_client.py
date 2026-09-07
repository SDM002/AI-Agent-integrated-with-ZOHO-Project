"""
Shared async HTTP client — initialised once at startup, reused across all outbound requests to Zoho APIs.
"""
import httpx
from app.config import SETTINGS

# Shared async HTTP client (initialized at startup, reused across requests)
http_client: httpx.AsyncClient | None = None

# Initialize the shared HTTP client with configured timeout at application start
def init_http_client() -> None:
    global http_client
    http_client = httpx.AsyncClient(timeout=httpx.Timeout(SETTINGS.OAUTH_HTTP_TIMEOUT))

# Close the shared HTTP client during application shutdown
async def close_http_client() -> None:
    global http_client
    if http_client:
        await http_client.aclose()
        http_client = None

# Return the initialized HTTP client or raise if accessed before startup initialization.
def get_http() -> httpx.AsyncClient:
    if http_client is None:
        raise RuntimeError("HTTP client not initialised — call init_http_client() at startup.")
    return http_client
