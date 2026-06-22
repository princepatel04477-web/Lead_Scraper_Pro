"""Configuration for the local lead scraper."""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

DEFAULT_COUNTRY = "India"
DEFAULT_LIMIT = 50
DEFAULT_SOURCES = ["maps", "directory", "reddit", "instagram", "facebook"]
ALL_SOURCES = DEFAULT_SOURCES + ["linkedin"]
LINKEDIN_OPT_IN = "linkedin"

MAPS_MAX_SCROLLS = 20
MIN_ACTION_DELAY = 2.0
MAX_ACTION_DELAY = 5.0
DIRECTORY_MAX_REQUESTS_PER_MINUTE = 12
REQUEST_TIMEOUT_SECONDS = 15

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
]

SOCIAL_DOMAINS = ("facebook.com", "fb.com", "instagram.com", "linkedin.com", "x.com", "twitter.com", "youtube.com", "tiktok.com", "pinterest.com", "wa.me", "whatsapp.com")
FREE_BUILDER_DOMAINS = ("wixsite.com", "weebly.com", "wordpress.com", "blogspot.com", "sites.google.com", "business.site", "godaddysites.com", "carrd.co", "canva.site", "site123.me")

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "lead-scraper-pro/1.0 personal-use")
