"""Playwright Google Maps scraper with graceful block handling."""
from __future__ import annotations

import re
from urllib.parse import quote_plus
from lead_scraper import config
from lead_scraper.modules.website_checker import classify_url_only
from lead_scraper.utils.rate_limiter import RequestLogger, randomized_delay

BLOCK_TERMS = ("captcha", "unusual traffic", "sorry", "verify")


class MapsScraper:
    def __init__(self, dry_run: bool = False, request_logger: RequestLogger | None = None, headless: bool = True):
        self.dry_run = dry_run
        self.request_logger = request_logger or RequestLogger(dry_run)
        self.headless = headless

    def scrape(self, niche: str, city: str, country: str, limit: int) -> list[dict]:
        url = f"https://www.google.com/maps/search/{quote_plus(niche + ' ' + city + ' ' + country)}"
        self.request_logger.log("maps", "open", url)
        if self.dry_run:
            return []
        from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
        leads = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            page = browser.new_page(user_agent=config.USER_AGENTS[0], viewport={"width": 1366, "height": 900})
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                randomized_delay(config.MIN_ACTION_DELAY, config.MAX_ACTION_DELAY)
                if any(term in page.content().lower() for term in BLOCK_TERMS):
                    browser.close(); return leads
                for _ in range(config.MAPS_MAX_SCROLLS):
                    cards = page.locator('a[href*="/maps/place/"]').all()
                    if len(cards) >= limit:
                        break
                    page.mouse.wheel(0, 6000)
                    randomized_delay(config.MIN_ACTION_DELAY, config.MAX_ACTION_DELAY)
                hrefs = []
                for card in page.locator('a[href*="/maps/place/"]').all()[:limit]:
                    href = card.get_attribute("href")
                    if href and href not in hrefs:
                        hrefs.append(href)
                for href in hrefs[:limit]:
                    self.request_logger.log("maps", "place", href)
                    page.goto(href, wait_until="domcontentloaded", timeout=30000)
                    randomized_delay(config.MIN_ACTION_DELAY, config.MAX_ACTION_DELAY)
                    leads.append(self._extract(page, niche))
            except PlaywrightTimeoutError:
                pass
            finally:
                browser.close()
        return [lead for lead in leads if lead.get("business_name")]

    def _extract(self, page, niche: str) -> dict:
        def text(selector: str) -> str:
            try:
                return page.locator(selector).first.text_content(timeout=2500).strip()
            except Exception:
                return ""
        def attr(selector: str, name: str) -> str:
            try:
                return page.locator(selector).first.get_attribute(name, timeout=2500) or ""
            except Exception:
                return ""
        website = attr('a[data-item-id="authority"]', "href")
        reviews_text = text('span[aria-label*="review"]')
        nums = re.findall(r"[\d,]+", reviews_text)
        return {"business_name": text("h1"), "category": text('button[jsaction*="category"]') or niche, "phone": attr('button[data-item-id^="phone:"]', "aria-label").replace("Phone: ", ""), "address": attr('button[data-item-id="address"]', "aria-label").replace("Address: ", ""), "website_url": website or "NONE", "website_status": classify_url_only(website), "instagram_handle": "", "facebook_page": "", "email": "", "rating": text('div.F7nice span[aria-hidden="true"]'), "review_count": nums[0].replace(",", "") if nums else "", "found_in_sources": "maps", "notes": ""}
