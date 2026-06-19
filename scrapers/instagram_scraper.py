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
    def scrape(
        self,
        niche: str,
        city: str,
        country: str,
        max_results: int = 40,
        progress_callback=None,
        lead_callback=None,
        stop_check=None,
    ) -> list[dict]:
        results: list[dict] = []
        seen_usernames: set[str] = set()
        hashtags = self._build_hashtags(niche, city)

        for tag in hashtags:
            if len(results) >= max_results:
                break
            if stop_check and stop_check():
                break
            if progress_callback:
                progress_callback(f"Instagram: searching #{tag}")

            try:
                hashtag = instaloader.Hashtag.from_name(self.L.context, tag)
            except Exception as e:
                logger.debug(f"Hashtag #{tag} not found: {e}")
                continue

            post_count = 0
            try:
                for post in hashtag.get_posts():
                    if len(results) >= max_results:
                        break
                    if stop_check and stop_check():
                        break
                    if post_count > 60:  # limit posts scanned per tag
                        break
                    post_count += 1

                    profile = post.owner_profile
                    username = profile.username

                    if username in seen_usernames:
                        continue
                    seen_usernames.add(username)

                    # only interested in business / creator accounts
                    if not (profile.is_business_account
                            or profile.business_category_name
                            or profile.biography):
                        continue

                    bio = profile.biography or ""
                    full_name = profile.full_name or ""
                    email = self._extract_email(bio)
                    phone = self._extract_phone(bio)

                    # skip if no contact info at all
                    if not email and not phone:
                        continue

                    # check city mention in bio/name/location loosely
                    combined = f"{bio} {full_name}".lower()
                    if city.lower() not in combined and country.lower() not in combined:
                        # only skip if we have plenty; keep if we're thin
                        if len(results) > 10:
                            continue

                    from utils.filters import classify_website_url
                    ext_url = profile.external_url or ""
                    biz = {
                        "name": full_name or username,
                        "category": profile.business_category_name or niche,
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
                    if lead_callback:
                        lead_callback(biz)
                    results.append(biz)
                    if progress_callback:
                        progress_callback(
                            f"Instagram [{len(results)}]: @{username}"
                        )
            except Exception as e:
                logger.warning(f"Error processing #{tag}: {e}")
                continue

        return results
