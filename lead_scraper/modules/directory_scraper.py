"""Public local-directory scraper."""
from __future__ import annotations

import random
from urllib.parse import quote_plus

from lead_scraper import config
from lead_scraper.modules.website_checker import classify_url_only
from lead_scraper.utils.rate_limiter import RateLimiter, RequestLogger

BLOCK_TERMS = ("captcha", "unusual traffic", "access denied", "blocked")


def _lead(name="", category="", phone="", address="", website="", source="directory"):
    return {"business_name": name, "category": category, "phone": phone, "address": address, "website_url": website or "NONE", "website_status": classify_url_only(website), "found_in_sources": source, "rating": "", "review_count": "", "email": "", "instagram_handle": "", "facebook_page": "", "notes": ""}


class DirectoryScraper:
    def __init__(self, dry_run: bool = False, request_logger: RequestLogger | None = None):
        self.dry_run = dry_run
        self.request_logger = request_logger or RequestLogger(dry_run)
        self.limiter = RateLimiter(config.DIRECTORY_MAX_REQUESTS_PER_MINUTE)

    def scrape(self, niche: str, city: str, country: str, limit: int) -> list[dict]:
        urls = self._urls(niche, city, country)
        results: list[dict] = []
        for source, url in urls:
            if len(results) >= limit:
                break
            self.request_logger.log(source, "fetch", url)
            if self.dry_run:
                continue
            self.limiter.wait()
            try:
                import requests
                from bs4 import BeautifulSoup
                resp = requests.get(url, timeout=config.REQUEST_TIMEOUT_SECONDS, headers={"User-Agent": random.choice(config.USER_AGENTS), "Accept-Language": "en-US,en;q=0.9"})
            except requests.RequestException:
                continue
            if resp.status_code >= 400 or any(term in resp.text.lower() for term in BLOCK_TERMS):
                break
            results.extend(self._parse(resp.text, source, niche)[: max(0, limit - len(results))])
        return results[:limit]

    def _urls(self, niche: str, city: str, country: str) -> list[tuple[str, str]]:
        qn, qc = quote_plus(niche), quote_plus(city)
        if country.strip().lower() == "india":
            return [("justdial", f"https://www.justdial.com/{quote_plus(city)}/{quote_plus(niche).replace('+', '-')}") , ("sulekha", f"https://www.sulekha.com/{quote_plus(niche).replace('+', '-')}/{quote_plus(city)}")]
        return [("yellowpages", f"https://www.yellowpages.com/search?search_terms={qn}&geo_location_terms={qc}")]

    def _parse(self, html: str, source: str, niche: str) -> list[dict]:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("div.result, div.listing, div.info, div.store-details, div.listing-item")
        leads = []
        for card in cards:
            name_el = card.select_one("a.business-name, h2 a, .listing-name a, .jcn a, h3, h2")
            phone_el = card.select_one(".phones, .phone, .contact-info .tel, [class*=phone]")
            addr_el = card.select_one(".adr, .address, .listing-address, [class*=address]")
            web_el = card.select_one('a[href^="http"]')
            name = name_el.get_text(" ", strip=True) if name_el else ""
            if not name:
                continue
            website = web_el.get("href", "") if web_el else ""
            if any(d in website for d in ("yellowpages", "justdial", "sulekha", "yelp")):
                website = ""
            leads.append(_lead(name=name, category=niche, phone=phone_el.get_text(" ", strip=True) if phone_el else "", address=addr_el.get_text(" ", strip=True) if addr_el else "", website=website, source=source))
        return leads
