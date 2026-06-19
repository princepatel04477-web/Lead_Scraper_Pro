"""
Yellow Pages / Yelp Scraper
───────────────────────────
Uses requests + BeautifulSoup to scrape business directories.
Falls back between yellowpages.com, yellowpages.ca, yelp.com
"""

import re
import time
import random
import logging
import concurrent.futures
import requests
from bs4 import BeautifulSoup

import config

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": random.choice(config.USER_AGENTS),
    "Accept-Language": "en-US,en;q=0.9",
}


class YellowPagesScraper:
    """Scrape YellowPages or Yelp listings."""

    def scrape(
        self,
        niche: str,
        city: str,
        country: str,
        max_results: int = 40,
        progress_callback=None,
    ) -> list[dict]:

        results: list[dict] = []
        num_agents = 10
        leads_per_agent = max(1, max_results // num_agents)

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_agents) as executor:
            futures = []
            for page in range(1, num_agents + 1):
                futures.append(executor.submit(self._agent_scrape, niche, city, country, page, leads_per_agent, progress_callback))

            for future in concurrent.futures.as_completed(futures):
                try:
                    res = future.result()
                    for biz in res:
                        if len(results) < max_results:
                            results.append(biz)
                except Exception as e:
                    logger.warning(f"Agent scrape error: {e}")

        # Fallback to Yelp if we still need more leads
        if len(results) < max_results:
            results += self._scrape_yelp(niche, city, max_results - len(results), progress_callback)

        return results[:max_results]


    def _agent_scrape(self, niche: str, city: str, country: str, page: int, max_results: int, callback) -> list[dict]:
        results = []
        country_lower = country.lower().strip()
        if "canada" in country_lower:
            base = "https://www.yellowpages.ca"
            search_url = f"{base}/search/si/1/{niche.replace(' ', '+')}/{city.replace(' ', '+')}"
        elif "india" in country_lower:
            base = "https://www.justdial.com"
            search_url = f"{base}/{city}/{niche.replace(' ', '-')}"
        else:  # default US
            base = "https://www.yellowpages.com"
            search_url = f"{base}/search?search_terms={niche.replace(' ', '+')}&geo_location_terms={city.replace(' ', '+')}"

        page_url = search_url if page == 1 else f"{search_url}&page={page}"
        try:
            resp = requests.get(page_url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                return results
        except Exception as e:
            logger.warning(f"YellowPages request failed: {e}")
            return results

        soup = BeautifulSoup(resp.text, "html.parser")
        listings = soup.select("div.result, div.listing, div.search-results div.listing-item")
        if not listings:
            listings = soup.select("div.info")

        for item in listings:
            if len(results) >= max_results:
                break
            biz = self._parse_yp_listing(item)
            if biz and biz.get("name"):
                biz["source"] = "YellowPages"
                results.append(biz)
                if callback:
                    callback(f"YellowPages [{len(results)}]: {biz['name']}")

        return results


    def _scrape_yellowpages(
        self, niche, city, country, max_results, callback
    ) -> list[dict]:
        results = []

        # choose domain by country
        country_lower = country.lower().strip()
        if "canada" in country_lower:
            base = "https://www.yellowpages.ca"
            search_url = f"{base}/search/si/1/{niche.replace(' ', '+')}/{city.replace(' ', '+')}"
        elif "india" in country_lower:
            base = "https://www.justdial.com"
            search_url = f"{base}/{city}/{niche.replace(' ', '-')}"
        else:  # default US
            base = "https://www.yellowpages.com"
            search_url = f"{base}/search?search_terms={niche.replace(' ', '+')}&geo_location_terms={city.replace(' ', '+')}"

        if callback:
            callback(f"YellowPages: fetching {search_url}")

        for page in range(1, 6):  # up to 5 pages
            if len(results) >= max_results:
                break

            page_url = search_url if page == 1 else f"{search_url}&page={page}"
            try:
                resp = requests.get(page_url, headers=HEADERS, timeout=15)
                if resp.status_code != 200:
                    break
            except Exception as e:
                logger.warning(f"YellowPages request failed: {e}")
                break

            soup = BeautifulSoup(resp.text, "html.parser")

            # yellowpages.com structure
            listings = soup.select("div.result, div.listing, div.search-results div.listing-item")
            if not listings:
                listings = soup.select("div.info")  # alternate selector

            for item in listings:
                if len(results) >= max_results:
                    break

                biz = self._parse_yp_listing(item)
                if biz and biz.get("name"):
                    biz["source"] = "YellowPages"
                    results.append(biz)
                    if callback:
                        callback(f"YellowPages [{len(results)}]: {biz['name']}")

            time.sleep(random.uniform(1.5, 3.0))

        return results

    def _parse_yp_listing(self, item) -> dict:
        biz = {}

        # Name
        name_el = item.select_one(
            "a.business-name, h2 a, .listing-name a, .jcn a"
        )
        biz["name"] = name_el.get_text(strip=True) if name_el else ""

        # Phone
        phone_el = item.select_one(
            "div.phones, .phone, .contact-info .tel"
        )
        biz["phone"] = phone_el.get_text(strip=True) if phone_el else ""

        # Address
        addr_el = item.select_one(
            "div.adr, .address, .listing-address, .cont_fl_addr"
        )
        biz["address"] = addr_el.get_text(" ", strip=True) if addr_el else ""

        # Website
        website_el = item.select_one('a[href*="http"]:not([href*="yellowpages"])')
        if website_el:
            href = website_el.get("href", "")
            if "yellowpages" not in href and "yelp" not in href:
                biz["website"] = href
            else:
                biz["website"] = ""
        else:
            biz["website"] = ""

        # Category
        cat_el = item.select_one(".categories a, .category")
        biz["category"] = cat_el.get_text(strip=True) if cat_el else ""

        from utils.filters import classify_website_url
        biz["rating"] = ""
        biz["reviews"] = ""
        biz["maps_url"] = ""
        biz["email"] = ""
        biz["instagram"] = ""
        biz["website_status"] = classify_website_url(biz.get("website", ""))

        return biz

    # ── Yelp ────────────────────────────────────────────
    def _scrape_yelp(self, niche, city, max_results, callback) -> list[dict]:
        results = []
        search_url = (
            f"https://www.yelp.com/search?"
            f"find_desc={niche.replace(' ', '+')}"
            f"&find_loc={city.replace(' ', '+')}"
        )

        if callback:
            callback(f"Yelp: fetching listings…")

        try:
            resp = requests.get(search_url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                return results
        except Exception:
            return results

        soup = BeautifulSoup(resp.text, "html.parser")

        # Yelp search result cards
        cards = soup.select('div[data-testid="serp-ia-card"], li.css-1l4w6pd')
        if not cards:
            cards = soup.select("div.container__09f24__FeTO6")

        from utils.filters import classify_website_url
        for card in cards[:max_results]:
            biz = {}
            name_el = card.select_one("a.css-19v1rkv, h3 a, a[name]")
            biz["name"] = name_el.get_text(strip=True) if name_el else ""

            phone_el = card.select_one("p.css-1p9ibgf")
            biz["phone"] = phone_el.get_text(strip=True) if phone_el else ""

            biz["address"] = ""
            biz["website"] = ""
            biz["instagram"] = ""
            biz["website_status"] = "No Website"
            biz["category"] = niche
            biz["rating"] = ""
            biz["reviews"] = ""
            biz["maps_url"] = ""
            biz["email"] = ""
            biz["source"] = "Yelp"

            if biz["name"]:
                results.append(biz)
                if callback:
                    callback(f"Yelp [{len(results)}]: {biz['name']}")

        return results
