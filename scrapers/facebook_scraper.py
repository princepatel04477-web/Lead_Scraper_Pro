"""
Facebook Scraper
────────────────
Uses Selenium to search Google for Facebook pages and extract details from the profiles.
"""

import time
import random
import re
import logging
import urllib.parse
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    StaleElementReferenceException,
)
from webdriver_manager.chrome import ChromeDriverManager

import config
from utils.filters import classify_website_url

logger = logging.getLogger(__name__)


class FacebookScraper:
    """Scrape Facebook page details via Google Search and Facebook profile pages."""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None

    def _build_driver(self):
        opts = Options()
        if self.headless:
            opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument("--lang=en-US")
        ua = random.choice(config.USER_AGENTS)
        opts.add_argument(f"--user-agent={ua}")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=opts)
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "Object.defineProperty(navigator,'webdriver',"
                       "{get:()=>undefined})"},
        )
        return driver

    def _handle_google_consent(self):
        """Dismiss Google's cookie/consent dialog if it appears."""
        consent_selectors = [
            "//button[contains(.,'Accept all')]",
            "//button[contains(.,'I agree')]",
            "//div[contains(text(),'Accept all')]",
            "//button[contains(.,'Accept All')]"
        ]
        for selector in consent_selectors:
            try:
                btn = self.driver.find_element(By.XPATH, selector)
                btn.click()
                time.sleep(1)
                break
            except Exception:
                pass

    def _handle_facebook_consent(self, driver):
        """Dismiss Facebook cookie consent or close login overlays."""
        # Click cookie consent buttons
        consent_selectors = [
            "//span[contains(text(), 'Allow all cookies')]",
            "//span[contains(text(), 'Decline optional cookies')]",
            "//span[contains(text(), 'Only allow essential cookies')]",
            "//span[contains(text(), 'Decline')]",
            "//span[contains(text(), 'Accept All')]",
            "//span[contains(text(), 'Accept all')]",
            "//div[@aria-label='Decline optional cookies']",
            "//div[@aria-label='Allow all cookies']",
            "//button[contains(., 'Decline')]",
            "//button[contains(., 'Accept All')]",
        ]
        for selector in consent_selectors:
            try:
                btn = driver.find_element(By.XPATH, selector)
                if btn.is_displayed():
                    btn.click()
                    time.sleep(1)
                    break
            except Exception:
                pass

        # Close login prompts if present
        close_selectors = [
            "//div[@aria-label='Close']",
            "//div[@aria-label='close']",
            "//div[@role='dialog']//div[@aria-label='Close']",
        ]
        for selector in close_selectors:
            try:
                btn = driver.find_element(By.XPATH, selector)
                btn.click()
                time.sleep(1)
            except Exception:
                pass

    def _normalize_facebook_url(self, url: str) -> Optional[str]:
        """Normalize Facebook URLs to avoid duplicate visits."""
        if "/url?" in url:
            from urllib.parse import urlparse, parse_qs
            try:
                parsed = urlparse(url)
                qs = parse_qs(parsed.query)
                if "q" in qs:
                    url = qs["q"][0]
            except Exception:
                pass

        url = url.strip()
        if "facebook.com" not in url and "fb.com" not in url:
            return None

        from urllib.parse import urlparse, parse_qs
        try:
            parsed = urlparse(url)
            path = parsed.path
            if "profile.php" in path:
                qs = parse_qs(parsed.query)
                if "id" in qs:
                    return f"https://www.facebook.com/profile.php?id={qs['id'][0]}"

            parts = [p for p in path.split("/") if p]
            if parts:
                first_part = parts[0]
                ignored = [
                    "sharer", "login", "policies", "help", "pages", "groups",
                    "business", "ads", "campaign", "search", "events",
                    "marketplace", "recover", "reg", "r.php", "checkpoint"
                ]
                if first_part.lower() not in ignored:
                    if first_part.lower() == "people" and len(parts) > 2:
                        return f"https://www.facebook.com/people/{parts[1]}/{parts[2]}"
                    return f"https://www.facebook.com/{first_part}"
        except Exception:
            pass

        return None

    def _extract_redirect_url(self, href: str) -> str:
        """Parse redirect links from Facebook to get external URL."""
        from urllib.parse import urlparse, parse_qs, unquote
        try:
            if "l.facebook.com" in href or "facebook.com/l.php" in href:
                parsed = urlparse(href)
                qs = parse_qs(parsed.query)
                if "u" in qs:
                    return unquote(qs["u"][0])
        except Exception:
            pass
        return href

    def _scrape_single_profile(self, fb_url: str, niche: str, city: str) -> Optional[dict]:
        """Scrape a single Facebook profile page for business details. Thread-safe."""
        driver = self._build_driver()
        try:
            driver.get(fb_url)
            time.sleep(random.uniform(3.0, 4.5))
            self._handle_facebook_consent(driver)

            # Extract Name
            name = ""
            try:
                h1_el = driver.find_element(By.TAG_NAME, "h1")
                name = h1_el.text.strip()
            except Exception:
                pass

            if not name:
                title = driver.title
                name = title
                for sep in [" - Home", " - About", " - Profile", " | Facebook", " - Facebook"]:
                    if sep in title:
                        name = name.split(sep)[0]
                name = name.strip()

            if not name:
                return None

            # Extract details from anchors & text
            email = ""
            phone = ""
            website = ""
            instagram = ""
            address = ""
            category = niche
            rating = ""
            reviews = ""

            # Scan elements text/body text
            body_text = ""
            try:
                body_text = driver.find_element(By.TAG_NAME, "body").text
            except Exception:
                pass

            # Category
            cat_match = re.search(r"Page\s*·\s*([^\n]+)", body_text)
            if cat_match:
                category = cat_match.group(1).strip()

            # Rating and reviews
            rating_match = re.search(
                r"Rating\s*·\s*([0-9.]+)\s*\(\s*([0-9,]+)\s*reviews?\s*\)",
                body_text,
                re.IGNORECASE
            )
            if rating_match:
                rating = rating_match.group(1).strip()
                reviews = rating_match.group(2).replace(",", "").strip()

            # Scan anchor tags for email, phone, website, instagram
            anchors = driver.find_elements(By.TAG_NAME, "a")
            for anchor in anchors:
                try:
                    href = anchor.get_attribute("href")
                    if not href:
                        continue

                    if href.startswith("mailto:"):
                        email = href.replace("mailto:", "").split("?")[0].strip()
                    elif href.startswith("tel:"):
                        phone = href.replace("tel:", "").strip()
                    elif "l.facebook.com/l.php" in href or "facebook.com/l.php" in href:
                        target = self._extract_redirect_url(href)
                        if target:
                            target_lower = target.lower()
                            if "instagram.com" in target_lower:
                                instagram = target
                            elif not any(d in target_lower for d in ["facebook.com", "fb.com", "threads.net", "twitter.com", "youtube.com"]):
                                website = target
                    else:
                        href_lower = href.lower()
                        if "instagram.com" in href_lower:
                            instagram = href
                        elif not any(d in href_lower for d in ["facebook.com", "fb.com", "threads.net", "twitter.com", "youtube.com", "javascript:", "google.com"]):
                            if not website and href.startswith("http"):
                                website = href
                except Exception:
                    pass

            # Fallbacks via regex if empty
            if not email:
                email_match = re.search(
                    r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", body_text
                )
                if email_match:
                    email = email_match.group(0)

            if not phone:
                phone_match = re.search(
                    r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
                    body_text
                )
                if phone_match:
                    phone = phone_match.group(0).strip()

            # Extract Address from text lines containing city
            lines = [line.strip() for line in body_text.split("\n") if line.strip()]
            for line in lines:
                if city.lower() in line.lower():
                    if "@" in line or "http" in line or "Page ·" in line:
                        continue
                    if any(w in line.lower() for w in ["rating", "reviews", "followers", "likes", "about", "photos", "videos"]):
                        continue
                    if len(line) < 100:
                        address = line
                        break

            return {
                "name": name,
                "category": category,
                "address": address,
                "phone": phone,
                "email": email,
                "website": website,
                "website_status": classify_website_url(website),
                "instagram": instagram,
                "rating": rating,
                "reviews": reviews,
                "maps_url": fb_url,
                "source": "Facebook"
            }
        except Exception as e:
            logger.warning(f"Error scraping Facebook page {fb_url}: {e}")
            return None
        finally:
            driver.quit()

    def scrape(
        self,
        niche: str,
        city: str,
        country: str,
        max_results: int = 40,
        progress_callback=None,
    ) -> list[dict]:
        """Scrape Facebook for business listings."""
        from utils.query_generator import generate_facebook_queries
        queries = generate_facebook_queries(niche, city, country)
        self.driver = self._build_driver()
        businesses: list[dict] = []
        unique_urls = []
        seen_urls = set()

        try:
            # 1. Search Google for site:facebook.com listings using expanded queries
            for q_idx, query in enumerate(queries):
                if len(unique_urls) >= max_results:
                    break

                # Search the first page (and second page for the primary query if needed)
                pages_to_search = [0]
                if q_idx == 0 and max_results > 10:
                    pages_to_search.append(10)

                for start in pages_to_search:
                    if len(unique_urls) >= max_results:
                        break

                    search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&start={start}"
                    if progress_callback:
                        progress_callback(f"Facebook: searching Google for '{query}'…")

                    self.driver.get(search_url)
                    time.sleep(random.uniform(2.5, 4.0))
                    self._handle_google_consent()

                    links = self.driver.find_elements(
                        By.XPATH, "//a[contains(@href, 'facebook.com') or contains(@href, 'fb.com')]"
                    )
                    for link in links:
                        try:
                            href = link.get_attribute("href")
                            if href:
                                norm = self._normalize_facebook_url(href)
                                if norm and norm not in seen_urls:
                                    seen_urls.add(norm)
                                    unique_urls.append(norm)
                        except Exception:
                            pass

            unique_urls = unique_urls[:max_results]
            if progress_callback:
                progress_callback(f"Facebook: Found {len(unique_urls)} page URLs. Scraping profiles…")

            # Close the main search driver to save RAM before starting parallel execution
            if self.driver:
                self.driver.quit()
                self.driver = None

            # 2. Visit each Facebook page to extract information
            if unique_urls:
                progress_lock = threading.Lock()
                completed_count = 0
                total_urls = len(unique_urls)

                def update_progress_status(business_name, success=True):
                    nonlocal completed_count
                    with progress_lock:
                        completed_count += 1
                        if progress_callback:
                            if success and business_name:
                                progress_callback(f"Facebook [{completed_count}/{total_urls}]: {business_name}")
                            else:
                                progress_callback(f"Facebook progress: {completed_count}/{total_urls} profiles completed")

                with ThreadPoolExecutor(max_workers=12) as executor:
                    futures = {
                        executor.submit(self._scrape_single_profile, url, niche, city): url
                        for url in unique_urls
                    }

                    for future in as_completed(futures):
                        url = futures[future]
                        try:
                            result = future.result()
                            if result:
                                businesses.append(result)
                                name = result.get("name", "Unknown")
                                update_progress_status(name, success=True)
                            else:
                                update_progress_status(None, success=False)
                        except Exception as e:
                            logger.error(f"Exception scraping {url}: {e}")
                            update_progress_status(None, success=False)

        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None

        return businesses
