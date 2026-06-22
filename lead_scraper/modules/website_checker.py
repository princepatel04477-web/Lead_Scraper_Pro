"""Website classification utilities."""
from __future__ import annotations

from urllib.parse import urlparse

from lead_scraper import config


def classify_url_only(url: str) -> str:
    if not url or not str(url).strip():
        return "no_website"
    lower = str(url).lower()
    if any(domain in lower for domain in config.SOCIAL_DOMAINS):
        return "no_website"
    if any(domain in lower for domain in config.FREE_BUILDER_DOMAINS):
        return "outdated"
    return "modern"


def check_website(url: str, dry_run: bool = False, request_logger=None) -> str:
    preliminary = classify_url_only(url)
    if preliminary != "modern":
        return preliminary
    target = url if str(url).startswith(("http://", "https://")) else f"https://{url}"
    if request_logger:
        request_logger.log("website", "fetch", target)
    if dry_run:
        return preliminary
    try:
        import requests
        from bs4 import BeautifulSoup
        resp = requests.get(target, timeout=config.REQUEST_TIMEOUT_SECONDS, headers={"User-Agent": config.USER_AGENTS[0]}, allow_redirects=True)
    except requests.RequestException:
        return "outdated"
    if resp.status_code >= 400:
        return "outdated"
    soup = BeautifulSoup(resp.text, "html.parser")
    has_ssl = urlparse(resp.url).scheme == "https"
    has_viewport = soup.find("meta", attrs={"name": "viewport"}) is not None
    html = resp.text.lower()
    if any(sig in html for sig in ("under construction", "coming soon", "domain is for sale", "domain expired", "parked domain")):
        return "outdated"
    return "modern" if has_ssl and has_viewport else "outdated"


def annotate_websites(leads: list[dict], dry_run: bool = False, request_logger=None) -> list[dict]:
    for lead in leads:
        url = lead.get("website_url") or lead.get("website") or ""
        lead["website_url"] = url or "NONE"
        lead["website_status"] = lead.get("website_status") or check_website(url, dry_run, request_logger)
    return leads
