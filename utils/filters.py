"""
Filtering & deduplication utilities
"""

import re
from difflib import SequenceMatcher
import config


def is_real_website(url: str) -> bool:
    """Return True if the URL is a genuine business website
    (not just a social media profile)."""
    if not url or not url.strip():
        return False
    url_lower = url.lower().strip()
    for domain in config.SOCIAL_DOMAINS:
        if domain in url_lower:
            return False
    return True


def classify_website_url(url: str) -> str:
    """Classify a website URL as 'No Website', 'Moderate Website', or 'Good Website'."""
    if not url or not url.strip():
        return "No Website"
    url_lower = url.lower().strip()
    for domain in config.SOCIAL_DOMAINS:
        if domain in url_lower:
            return "No Website"
    for domain in config.FREE_WEBSITE_DOMAINS:
        if domain in url_lower:
            return "Moderate Website"
    return "Good Website"


def filter_no_website(businesses: list[dict]) -> list[dict]:
    """Keep only businesses that do NOT have a real website.
    A Facebook / Instagram page does NOT count as a website."""
    return [
        biz for biz in businesses
        if not is_real_website(biz.get("website", ""))
    ]



def _normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def deduplicate(businesses: list[dict], threshold: float = 0.80) -> list[dict]:
    """Remove near-duplicate businesses using name similarity.
    When merging, keep the record with more data."""
    if not businesses:
        return []

    unique: list[dict] = []

    for biz in businesses:
        norm = _normalize(biz.get("name", ""))
        is_dup = False

        for i, existing in enumerate(unique):
            existing_norm = _normalize(existing.get("name", ""))
            ratio = SequenceMatcher(None, norm, existing_norm).ratio()

            if ratio >= threshold:
                # merge: fill blanks in existing with data from biz
                for key in biz:
                    if biz[key] and not existing.get(key):
                        unique[i][key] = biz[key]
                is_dup = True
                break

        if not is_dup:
            unique.append(biz.copy())

    return unique
