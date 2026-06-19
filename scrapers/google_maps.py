"""
Google Maps Scraper
───────────────────
Uses Selenium to:
  1. Search Google Maps for "{niche} in {city}, {country}"
  2. Scroll the results panel to load listings
  3. Click each listing and extract details
  4. Return list of dicts with name/address/phone/website/rating
"""

import time
import random
import re
import logging
import concurrent.futures

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
)
from webdriver_manager.chrome import ChromeDriverManager

import config

logger = logging.getLogger(__name__)


class GoogleMapsScraper:
    """Scrape Google Maps business listings."""

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.driver = None

    # ── Browser setup ───────────────────────────────────
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

        import os
        if os.path.exists("/usr/bin/chromium-browser"):
            opts.binary_location = "/usr/bin/chromium-browser"
        elif os.path.exists("/usr/bin/chromium"):
            opts.binary_location = "/usr/bin/chromium"

        if os.path.exists("/usr/bin/chromedriver"):
            service = Service("/usr/bin/chromedriver")
        else:
            service = Service(ChromeDriverManager().install())
            
        driver = webdriver.Chrome(service=service, options=opts)
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "Object.defineProperty(navigator,'webdriver',"
                       "{get:()=>undefined})"},
        )
        return driver

    # ── Accept cookie / consent banner ──────────────────
    def _handle_consent(self):
        """Click 'Accept all' if Google shows a consent popup."""
        try:
            btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(.,'Accept all')]")
                )
            )
            btn.click()
            time.sleep(1)
        except TimeoutException:
            pass  # no consent dialog

    # ── Scroll the results feed ─────────────────────────
    def _scroll_feed(self, max_scrolls: int, callback=None):
        """Scroll the left-hand results panel to load more listings."""
        try:
            feed = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="feed"]'))
            )
        except TimeoutException:
            logger.warning("Could not find results feed.")
            return

        prev_count = 0
        stale_rounds = 0

        for i in range(max_scrolls):
            self.driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight", feed
            )
            time.sleep(config.GOOGLE_MAPS_SCROLL_PAUSE + random.uniform(0.3, 1.0))

            links = feed.find_elements(By.CSS_SELECTOR, 'a[href*="/maps/place/"]')
            cur_count = len(links)
            if callback:
                callback(f"Scrolling… {cur_count} listings loaded")

            # check for "end of list" text
            try:
                feed.find_element(
                    By.XPATH, './/*[contains(text(),"end of results")]'
                )
                logger.info("Reached end of results.")
                break
            except NoSuchElementException:
                pass

            if cur_count == prev_count:
                stale_rounds += 1
                if stale_rounds >= 3:
                    break
            else:
                stale_rounds = 0
            prev_count = cur_count

    # ── Extract one business detail ─────────────────────
    def _extract_detail(self, driver=None) -> dict | None:
        driver = driver or getattr(self, 'driver', None)
        biz = {}

        # Name
        try:
            h1 = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "h1.DUwDvf, h1.fontHeadlineLarge")
                )
            )
            biz["name"] = h1.text.strip()
        except TimeoutException:
            # fallback: grab whatever h1 is there
            try:
                biz["name"] = driver.find_element(By.TAG_NAME, "h1").text.strip()
            except Exception:
                return None

        if not biz["name"]:
            return None

        # Category / type
        try:
            cat = driver.find_element(
                By.CSS_SELECTOR, 'button[jsaction*="category"]'
            )
            biz["category"] = cat.text.strip()
        except NoSuchElementException:
            biz["category"] = ""

        # Address
        try:
            el = driver.find_element(
                By.CSS_SELECTOR, 'button[data-item-id="address"]'
            )
            aria = el.get_attribute("aria-label") or ""
            biz["address"] = aria.replace("Address: ", "").strip()
        except NoSuchElementException:
            biz["address"] = ""

        # Phone
        try:
            el = driver.find_element(
                By.CSS_SELECTOR, 'button[data-item-id^="phone:"]'
            )
            raw = el.get_attribute("data-item-id") or ""
            biz["phone"] = raw.replace("phone:tel:", "").strip()
        except NoSuchElementException:
            biz["phone"] = ""

        # Website
        try:
            el = driver.find_element(
                By.CSS_SELECTOR, 'a[data-item-id="authority"]'
            )
            biz["website"] = el.get_attribute("href") or ""
        except NoSuchElementException:
            biz["website"] = ""

        # Rating & review count
        try:
            rating_el = driver.find_element(
                By.CSS_SELECTOR, 'div.F7nice span[aria-hidden="true"]'
            )
            biz["rating"] = rating_el.text.strip()
        except NoSuchElementException:
            biz["rating"] = ""

        try:
            reviews_el = driver.find_element(
                By.CSS_SELECTOR, 'div.F7nice span[aria-label*="review"]'
            )
            text = reviews_el.get_attribute("aria-label") or ""
            nums = re.findall(r"[\d,]+", text)
            biz["reviews"] = nums[0].replace(",", "") if nums else ""
        except NoSuchElementException:
            biz["reviews"] = ""

        # Google Maps URL of this place
        biz["maps_url"] = driver.current_url

        # Source tag
        biz["source"] = "Google Maps"

        return biz

    def _extract_ig_redirect_link(self, href: str) -> str:
        from urllib.parse import urlparse, parse_qs
        try:
            if "l.instagram.com" in href or "instagram.com/l.php" in href:
                parsed = urlparse(href)
                qs = parse_qs(parsed.query)
                if "u" in qs:
                    return qs["u"][0]
        except Exception:
            pass
        return href

    def _fetch_ig_link_via_instaloader(self, instagram_url: str) -> str:
        import instaloader
        try:
            L = instaloader.Instaloader(
                download_pictures=False,
                download_videos=False,
                download_video_thumbnails=False,
                download_comments=False,
                save_metadata=False,
                compress_json=False,
            )
            # extract username
            match = re.search(r"instagram\.com/([a-zA-Z0-9_\.]+)", instagram_url)
            if match:
                username = match.group(1)
                profile = instaloader.Profile.from_name(L.context, username)
                return profile.external_url or ""
        except Exception as e:
            logger.debug(f"Instaloader failed to fetch profile {instagram_url}: {e}")
        return ""

    def _classify_page_load(self, url: str, driver=None) -> str:
        driver = driver or getattr(self, 'driver', None)
        url_lower = url.lower()
        
        # Check page text for errors using selenium
        try:
            title = driver.title.lower()
            if any(err in title for err in ["404", "not found", "error", "site can't be reached", "server not found", "dns_probe_finished"]):
                return "No Website"
                
            body_element = driver.find_element(By.TAG_NAME, "body")
            body_text = body_element.text.lower()[:500] if body_element else ""
            if any(err in body_text for err in ["404 - file or directory not found", "page not found", "404 not found", "site cannot be reached"]):
                return "No Website"
        except Exception:
            pass
            
        # check if it is a free site domain
        for domain in config.FREE_WEBSITE_DOMAINS:
            if domain in url_lower:
                return "Moderate Website"
                
        # check if it is a social site
        for domain in config.SOCIAL_DOMAINS:
            if domain in url_lower:
                return "No Website"
                
        return "Good Website"

    def _verify_website_and_instagram(self, biz: dict, driver=None) -> dict:
        driver = driver or getattr(self, 'driver', None)
        url = biz.get("website", "").strip()
        biz["instagram"] = ""
        biz["website_status"] = "No Website"
        
        if not url:
            biz["website"] = ""
            return biz
            
        url_lower = url.lower()
        is_instagram = "instagram.com" in url_lower
        
        original_handle = driver.current_window_handle
        
        try:
            # open new tab
            driver.execute_script("window.open('about:blank', '_blank');")
            time.sleep(0.5)
            driver.switch_to.window(driver.window_handles[-1])
            
            logger.info(f"Opening website to verify: {url}")
            driver.get(url)
            time.sleep(3)
            
            final_url = driver.current_url
            if "instagram.com" in final_url.lower():
                is_instagram = True
                url = final_url
                
            if is_instagram:
                biz["instagram"] = url
                biz["website"] = ""
                
                # Check for links in Instagram profile page
                found_link = ""
                try:
                    # check for common redirect links
                    links = driver.find_elements(By.CSS_SELECTOR, "a[href*='l.instagram.com'], a[href*='instagram.com/l.php']")
                    for l in links:
                        href = l.get_attribute("href")
                        if href:
                            found_link = self._extract_ig_redirect_link(href)
                            if found_link:
                                break
                                
                    if not found_link:
                        # Scan all external links
                        all_links = driver.find_elements(By.TAG_NAME, "a")
                        for l in all_links:
                            href = l.get_attribute("href") or ""
                            if href and not any(d in href.lower() for d in ["instagram.com", "facebook.com", "threads.net", "javascript:"]):
                                found_link = href
                                break
                except Exception as e:
                    logger.debug(f"Error scanning Instagram links via Selenium: {e}")
                    
                if not found_link:
                    found_link = self._fetch_ig_link_via_instaloader(url)
                    
                if found_link:
                    logger.info(f"Found website in Instagram bio: {found_link}")
                    biz["website"] = found_link
                    try:
                        driver.get(found_link)
                        time.sleep(3)
                        final_bio_url = driver.current_url
                        biz["website_status"] = self._classify_page_load(final_bio_url, driver)
                    except Exception as e:
                        logger.warning(f"Failed to load Instagram bio website {found_link}: {e}")
                        biz["website_status"] = "No Website"
                else:
                    biz["website_status"] = "No Website"
            else:
                biz["website_status"] = self._classify_page_load(final_url, driver)
                biz["website"] = final_url
                
        except Exception as e:
            logger.warning(f"Error opening and verifying website {url}: {e}")
            biz["website_status"] = "No Website"
            
        finally:
            try:
                if len(driver.window_handles) > 1:
                    driver.close()
            except Exception:
                pass
            try:
                driver.switch_to.window(original_handle)
            except Exception:
                if driver.window_handles:
                    driver.switch_to.window(driver.window_handles[0])
                    
        return biz


    # ── Main public method ──────────────────────────────

    def _agent_scrape(self, query: str, max_results: int, progress_callback, broaden: bool, seen_names: set, seen_lock) -> list[dict]:
        driver = self._build_driver()
        businesses = []
        try:
            url = "https://www.google.com/maps/search/" + query.replace(" ", "+")
            if progress_callback:
                progress_callback(f"Opening Google Maps for: '{query}'…")
            driver.get(url)
            import time
            time.sleep(4)

            # handle consent
            try:
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                from selenium.webdriver.common.by import By
                from selenium.common.exceptions import TimeoutException
                btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'Accept all')]"))
                )
                btn.click()
                time.sleep(1)
            except Exception:
                pass

            if progress_callback:
                progress_callback(f"Scrolling to load listings for '{query}'…")

            # scroll feed
            try:
                feed = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="feed"]'))
                )
                import random
                prev_count = 0
                stale_rounds = 0
                for i in range(15):  # config.GOOGLE_MAPS_MAX_SCROLLS usually 15
                    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", feed)
                    time.sleep(2 + random.uniform(0.3, 1.0))

                    links = feed.find_elements(By.CSS_SELECTOR, 'a[href*="/maps/place/"]')
                    cur_count = len(links)

                    try:
                        feed.find_element(By.XPATH, './/*[contains(text(),"end of results")]')
                        break
                    except Exception:
                        pass

                    if cur_count == prev_count:
                        stale_rounds += 1
                        if stale_rounds >= 3:
                            break
                    else:
                        stale_rounds = 0
                    prev_count = cur_count
            except Exception as e:
                pass

            try:
                feed = driver.find_element(By.CSS_SELECTOR, 'div[role="feed"]')
                result_els = feed.find_elements(By.CSS_SELECTOR, 'a[href*="/maps/place/"]')
            except Exception:
                result_els = []

            total = min(len(result_els), max_results)
            if total <= 0:
                return businesses

            if progress_callback:
                progress_callback(f"[{query}] Found {len(result_els)} listings. Extracting top {total}…")

            for idx in range(len(result_els)):
                if len(businesses) >= max_results:
                    break
                try:
                    feed = driver.find_element(By.CSS_SELECTOR, 'div[role="feed"]')
                    links = feed.find_elements(By.CSS_SELECTOR, 'a[href*="/maps/place/"]')
                    if idx >= len(links):
                        break

                    el = links[idx]
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                    time.sleep(0.5)
                    el.click()
                    time.sleep(1.5 + random.uniform(0.2, 0.8))

                    biz = self._extract_detail(driver=driver)
                    if biz:
                        name_norm = biz["name"].lower().strip()
                        with seen_lock:
                            is_new = name_norm not in seen_names
                            if is_new:
                                seen_names.add(name_norm)

                        if is_new:
                            biz = self._verify_website_and_instagram(biz, driver=driver)
                            businesses.append(biz)
                            if progress_callback:
                                progress_callback(f"[{query}] [{len(businesses)}/{max_results}] {biz['name']}")

                    try:
                        back = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Back"], button[jsaction*="back"]')
                        back.click()
                    except Exception:
                        driver.back()
                    time.sleep(1.5)

                except Exception as exc:
                    try:
                        driver.back()
                        time.sleep(1)
                    except Exception:
                        pass
                    continue

        finally:
            driver.quit()

        return businesses


    def scrape(
        self,
        niche: str,
        city: str,
        country: str,
        max_results: int = 80,
        progress_callback=None,
        broaden: bool = False,
    ) -> list[dict]:
        """
        Parameters
        ----------
        niche : str      e.g. "interior design"
        city : str       e.g. "Toronto"
        country : str    e.g. "Canada"
        max_results : int
        progress_callback : callable(str)  optional status updater
        broaden : bool   whether to run wider search if results are low

        Returns
        -------
        list of dicts, each dict = one business
        """
        from utils.query_generator import generate_google_maps_queries
        queries = generate_google_maps_queries(niche, city, country, broaden=broaden)

        num_agents = 10
        leads_per_agent = max(1, max_results // num_agents)

        businesses: list[dict] = []
        seen_names = set()
        import threading
        seen_lock = threading.Lock()

        # Google maps doesn't paginate easily with start=N.
        # Instead of doing identical queries which wastes resources,
        # we just only run up to the number of unique queries we have.
        # We can broaden the queries artificially to match num_agents.
        if len(queries) < num_agents:
            additional = [
                f"{q} offices" for q in queries
            ] + [
                f"{q} services" for q in queries
            ] + [
                f"top {q}" for q in queries
            ]
            queries.extend(additional)

        agent_queries = queries[:num_agents]
        # Adjust leads_per_agent if we run fewer agents to still hit max_results
        actual_agents = len(agent_queries)
        if actual_agents > 0:
            leads_per_agent = max(1, max_results // actual_agents) + 1

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_agents) as executor:
            futures = []
            for q in agent_queries:
                futures.append(executor.submit(self._agent_scrape, q, leads_per_agent, progress_callback, broaden, seen_names, seen_lock))

            for future in concurrent.futures.as_completed(futures):
                try:
                    res = future.result()
                    for biz in res:
                        if len(businesses) < max_results:
                            businesses.append(biz)
                except Exception as e:
                    logger.warning(f"Agent scrape error: {e}")

        return businesses[:max_results]
