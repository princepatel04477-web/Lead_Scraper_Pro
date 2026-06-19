"""
Instagram Scraper
─────────────────
Uses the free `instaloader` library to:
  1. Search hashtags like #torontointeriordesign
  2. Find business accounts posting with location tags
  3. Extract bio info (email, phone from bio text)
"""

import re
import logging
import concurrent.futures
import instaloader
from typing import Optional

logger = logging.getLogger(__name__)


class InstagramScraper:
    """Scrape Instagram for business leads via hashtags & profiles."""

    def __init__(self):
        self.L = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
        )

    # ── helpers ─────────────────────────────────────────
    @staticmethod
    def _build_hashtags(niche: str, city: str) -> list[str]:
        """Generate likely hashtags."""
        niche_clean = niche.lower().replace(" ", "")
        city_clean = city.lower().replace(" ", "")
        return [
            f"{city_clean}{niche_clean}",
            f"{niche_clean}{city_clean}",
            f"{city_clean}{niche_clean.rstrip('s')}",  # singular
            f"{niche_clean}",
            f"{city_clean}business",
        ]

    @staticmethod
    def _extract_email(text: str) -> str:
        match = re.search(
            r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text or ""
        )
        return match.group(0) if match else ""

    @staticmethod
    def _extract_phone(text: str) -> str:
        match = re.search(
            r"[\+]?[(]?[0-9]{1,4}[)]?[-\s\./0-9]{7,15}", text or ""
        )
        return match.group(0).strip() if match else ""

    # ── Main scrape ─────────────────────────────────────

    def _agent_scrape(self, hashtag: str, city: str, country: str, max_results: int, progress_callback, seen_usernames: set, seen_lock) -> list[dict]:
        results = []
        try:
            L = instaloader.Instaloader(
                download_pictures=False,
                download_videos=False,
                download_video_thumbnails=False,
                download_comments=False,
                save_metadata=False,
                compress_json=False,
            )
            try:
                tag_obj = instaloader.Hashtag.from_name(L.context, hashtag)
            except Exception as e:
                logger.debug(f"Hashtag #{hashtag} not found: {e}")
                return results

            post_count = 0
            for post in tag_obj.get_posts():
                if len(results) >= max_results:
                    break
                if post_count > 60:
                    break
                post_count += 1

                profile = post.owner_profile
                username = profile.username

                with seen_lock:
                    if username in seen_usernames:
                        continue
                    seen_usernames.add(username)

                if not (profile.is_business_account or profile.business_category_name or profile.biography):
                    continue

                bio = profile.biography or ""
                full_name = profile.full_name or ""
                email = self._extract_email(bio)
                phone = self._extract_phone(bio)

                if not email and not phone:
                    continue

                combined = f"{bio} {full_name}".lower()
                if city.lower() not in combined and country.lower() not in combined:
                    if len(results) > 10:
                        continue

                from utils.filters import classify_website_url
                ext_url = profile.external_url or ""
                biz = {
                    "name": full_name or username,
                    "category": profile.business_category_name or "",
                    "address": "",
                    "phone": phone,
                    "email": email,
                    "website": ext_url,
                    "website_status": classify_website_url(ext_url),
                    "rating": "",
                    "reviews": "",
                    "instagram": f"https://instagram.com/{username}",
                    "followers": profile.mediacount,
                    "maps_url": "",
                    "source": "Instagram",
                }
                results.append(biz)
                if progress_callback:
                    progress_callback(f"Instagram [{hashtag}] [{len(results)}]: @{username}")
        except Exception as e:
            logger.warning(f"Error processing #{hashtag}: {e}")

        return results


    def scrape(
        self,
        niche: str,
        city: str,
        country: str,
        max_results: int = 40,
        progress_callback=None,
    ) -> list[dict]:
        results: list[dict] = []
        seen_usernames: set[str] = set()
        import threading
        seen_lock = threading.Lock()
        hashtags = self._build_hashtags(niche, city)

        num_agents = 10
        leads_per_agent = max(1, max_results // num_agents)

        # Do not blindly repeat the exact same hashtag to avoid duplicate effort.
        # Generate enough unique variations.
        agent_tags = hashtags[:]
        if len(agent_tags) < num_agents:
            more_tags = [t + "life" for t in hashtags] + [t + "style" for t in hashtags] + [t + "biz" for t in hashtags]
            agent_tags.extend(more_tags)
        agent_tags = agent_tags[:num_agents]

        actual_agents = len(agent_tags)
        if actual_agents > 0:
            leads_per_agent = max(1, max_results // actual_agents) + 1

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_agents) as executor:
            futures = []
            for tag in agent_tags:
                futures.append(executor.submit(self._agent_scrape, tag, city, country, leads_per_agent, progress_callback, seen_usernames, seen_lock))

            for future in concurrent.futures.as_completed(futures):
                try:
                    res = future.result()
                    for biz in res:
                        if len(results) < max_results:
                            results.append(biz)
                except Exception as e:
                    logger.warning(f"Agent scrape error: {e}")

        return results[:max_results]
