"""Zoho domain normalization — converts any Zoho API domain string into Projects API host format."""
import urllib.parse
from app.config import SETTINGS
from app.config.settings import ZOHO_PROJECTS_DOMAIN_MAP


def normalize_projects_domain(domain: str) -> str:
    if not domain:
        return SETTINGS.ZOHO_PROJECTS_API_DOMAIN

    raw = str(domain).strip()
    if raw.startswith("http://") or raw.startswith("https://"):
        raw = urllib.parse.urlparse(raw).netloc or raw

    raw = raw.strip().strip("/")

    for api_host, projects_host in ZOHO_PROJECTS_DOMAIN_MAP.items():
        if api_host in raw:
            return projects_host

    return raw
