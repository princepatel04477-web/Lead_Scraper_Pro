"""Search-engine-only social discovery for public snippets."""
from __future__ import annotations

import re
from urllib.parse import quote_plus, urlparse

from lead_scraper import config
from lead_scraper.utils.rate_limiter import RequestLogger


class SocialDiscovery:
    def __init__(self, dry_run: bool = False, request_logger: RequestLogger | None = None):
        self.dry_run = dry_run
        self.request_logger = request_logger or RequestLogger(dry_run)

    def scrape(self, platform: str, niche: str, city: str, country: str, limit: int) -> list[dict]:
        domain = {"instagram": "instagram.com", "facebook": "facebook.com", "linkedin": "linkedin.com/company"}[platform]
        query = f'site:{domain} "{niche}" "{city}"'
        url = f"https://www.google.com/search?q={quote_plus(query)}&num={min(limit, 20)}"
        self.request_logger.log(platform, "search", query)
        if self.dry_run:
            return []
        try:
            import requests
            from bs4 import BeautifulSoup
            resp = requests.get(url, timeout=config.REQUEST_TIMEOUT_SECONDS, headers={"User-Agent": config.USER_AGENTS[0]})
        except requests.RequestException:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        leads = []
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            if platform not in href:
                continue
            text = a.get_text(" ", strip=True)
            clean = self._clean_google_url(href)
            name = re.split(r"[-|•]", text)[0].strip()
            if not name or len(name) < 2:
                continue
            lead = {"business_name": name, "category": niche, "phone": "", "address": city, "website_url": "NONE", "website_status": "no_website", "found_in_sources": platform, "email": "", "rating": "", "review_count": "", "notes": "public search-result snippet"}
            if platform == "instagram":
                lead["instagram_handle"] = self._instagram_handle(clean)
                lead["facebook_page"] = ""
            elif platform == "facebook":
                lead["facebook_page"] = clean
                lead["instagram_handle"] = ""
            else:
                lead["notes"] = f"LinkedIn public result: {clean}"
                lead["instagram_handle"] = ""
                lead["facebook_page"] = ""
            leads.append(lead)
            if len(leads) >= limit:
                break
        return leads

    def _clean_google_url(self, href: str) -> str:
        match = re.search(r"/url\?q=([^&]+)", href)
        return match.group(1) if match else href

    def _instagram_handle(self, url: str) -> str:
        parts = [p for p in urlparse(url).path.split("/") if p]
        return f"@{parts[0]}" if parts else url
