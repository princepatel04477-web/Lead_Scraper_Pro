"""
config.py — Central settings for the lead scraper
"""

import os

# ── Paths ──────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Scraper settings ──────────────────────────────────
GOOGLE_MAPS_MAX_SCROLLS = 15          # how many times to scroll the results panel
GOOGLE_MAPS_SCROLL_PAUSE = 2          # seconds between scrolls
GOOGLE_MAPS_CLICK_PAUSE = 1.5         # seconds after clicking a result
PAGE_LOAD_TIMEOUT = 15                # max wait for page elements

# ── Anti-detection ────────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# ── Domains that count as "social media" not a real website ──
SOCIAL_DOMAINS = [
    "facebook.com", "fb.com",
    "instagram.com",
    "twitter.com", "x.com",
    "linkedin.com",
    "youtube.com",
    "tiktok.com",
    "pinterest.com",
    "wa.me", "whatsapp.com",
]

# ── Domains of free/basic website platforms (Moderate Website) ──
FREE_WEBSITE_DOMAINS = [
    "wixsite.com", "wix.com", "weebly.com", "wordpress.com",
    "linktr.ee", "carrd.co", "site123.me", "sites.google.com",
    "business.site", "canva.site", "godaddysites.com", "bio.link",
    "beacons.ai", "beacons.page", "taplink.cc", "squarespace.com",
]

