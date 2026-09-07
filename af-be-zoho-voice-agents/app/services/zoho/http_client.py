"""Zoho async HTTP client — stateless wrapper for Zoho v1 (form-data) and v3 (JSON) APIs."""
import asyncio
import httpx
from app.config import SETTINGS, logger
from app.services.zoho.domain import normalize_projects_domain


class ZohoAPIError(Exception):
    pass


class ZohoRateLimitError(ZohoAPIError):
    def __init__(self, retry_after: int = 1):
        self.retry_after = retry_after
        super().__init__(f"Zoho rate limited — retry after {retry_after}s")


class ZohoHttpClient:

    def __init__(
        self,
        access_token: str,
        api_domain: str = None,
        portal_id: str = None,
        portal_numeric_id: str = None,
        tenant_id: str = "default",
    ):
        base_domain      = normalize_projects_domain(api_domain or SETTINGS.ZOHO_PROJECTS_API_DOMAIN)
        pid              = portal_id
        pid_v3           = portal_numeric_id or pid

        if not pid and not pid_v3:
            raise ValueError(f"No Zoho portal ID available for user {tenant_id}. Please reconnect and select a portal.")

        self.portal_id   = pid
        self.tenant_id   = tenant_id

        self.base_url    = f"https://{base_domain}/restapi/portal/{pid}"
        self.v3_base_url = f"https://{base_domain}/api/v3/portal/{pid_v3}"

        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Zoho-oauthtoken {access_token}"},
            timeout=httpx.Timeout(
                connect=SETTINGS.ZOHO_TIMEOUT_CONNECT,
                read=SETTINGS.ZOHO_TIMEOUT_READ,
                write=SETTINGS.ZOHO_TIMEOUT_WRITE,
                pool=SETTINGS.ZOHO_TIMEOUT_POOL,
            ),
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.client.aclose()

    async def send(self, method: str, url: str, **kwargs) -> dict:
        safe         = method == "GET"
        max_attempts = SETTINGS.OAUTH_MAX_RETRIES

        for attempt in range(max_attempts):
            try:
                response = await self.client.request(method, url, **kwargs)

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 1))
                    logger.warning("Zoho rate limit", tenant=self.tenant_id, url=url, retry_after=retry_after)
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(retry_after)
                        continue
                    return {"success": False, "user_message": f"Zoho rate limited — retry after {retry_after}s"}

                if response.status_code >= 500 and safe and attempt < max_attempts - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue

                if not response.is_success:
                    logger.error("Zoho API error", tenant=self.tenant_id, method=method, status=response.status_code, body=response.text[:300])
                    try:
                        data = response.json()
                        msg = data.get("user_message") or data.get("error", {}).get("message") or response.text[:200]
                    except Exception:
                        msg = response.text[:200]
                    return {"success": False, "user_message": f"Zoho {response.status_code}: {msg}"}

                logger.debug("Zoho API", tenant=self.tenant_id, method=method, status=response.status_code)
                data = response.json() if response.text.strip() else {}
                return {"success": True, "value": data}

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                logger.error("Zoho network error", tenant=self.tenant_id, method=method, error=type(e).__name__)
                if safe and attempt < max_attempts - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return {"success": False, "user_message": f"Zoho network error: {type(e).__name__}"}
            except Exception as e:
                logger.exception("Zoho unexpected error", tenant=self.tenant_id)
                return {"success": False, "user_message": f"Unexpected error: {str(e)}"}

    # ── v1 methods (form-data) ───────────────────────────────────────────────

    async def get(self, path: str, params: dict = None) -> dict:
        return await self.send("GET", f"{self.base_url}{path}", params=params)

    async def post(self, path: str, data: dict = None) -> dict:
        return await self.send("POST", f"{self.base_url}{path}", json=data)

    async def post_form(self, path: str, data: dict = None) -> dict:
        return await self.send("POST", f"{self.base_url}{path}", data=data)

    async def patch_form(self, path: str, data: dict = None) -> dict:
        return await self.send("POST", f"{self.base_url}{path}", data=data)

    async def delete(self, path: str) -> dict:
        return await self.send("DELETE", f"{self.base_url}{path}")

    # ── v3 methods (JSON) ────────────────────────────────────────────────────

    async def get_v3(self, path: str, params: dict = None) -> dict:
        return await self.send("GET", f"{self.v3_base_url}{path}", params=params)

    async def post_v3(self, path: str, data: dict = None) -> dict:
        return await self.send("POST", f"{self.v3_base_url}{path}", json=data)

    async def post_form_v3(self, path: str, data: dict = None) -> dict:
        return await self.send("POST", f"{self.v3_base_url}{path}", data=data)

    async def patch_v3(self, path: str, data: dict = None) -> dict:
        return await self.send("PATCH", f"{self.v3_base_url}{path}", json=data)

    async def put_v3(self, path: str, data: dict = None) -> dict:
        return await self.send("PUT", f"{self.v3_base_url}{path}", json=data)

    async def delete_v3(self, path: str, data: dict = None) -> dict:
        return await self.send("DELETE", f"{self.v3_base_url}{path}", json=data)
