"""Official Reddit API intent finder."""
from __future__ import annotations

import re
from lead_scraper import config
from lead_scraper.utils.rate_limiter import RequestLogger

INTENT_RE = re.compile(r"\b(need|looking for|recommend|recommendation|hire|build|make).{0,40}\b(web ?site|web designer|web developer|site)\b", re.I)


class RedditFinder:
    def __init__(self, dry_run: bool = False, request_logger: RequestLogger | None = None):
        self.dry_run = dry_run
        self.request_logger = request_logger or RequestLogger(dry_run)

    def scrape(self, niche: str, city: str, country: str, limit: int) -> list[dict]:
        queries = [f'"{city}" "{niche}" "website"', f'"{city}" "need a website"', f'"{niche}" "web designer"']
        subreddits = [city.replace(" ", ""), "smallbusiness", "Entrepreneur"]
        for query in queries:
            self.request_logger.log("reddit", "search", query)
        if self.dry_run:
            return []
        if not (config.REDDIT_CLIENT_ID and config.REDDIT_CLIENT_SECRET):
            return []
        import praw
        reddit = praw.Reddit(client_id=config.REDDIT_CLIENT_ID, client_secret=config.REDDIT_CLIENT_SECRET, user_agent=config.REDDIT_USER_AGENT)
        results = []
        for sub in subreddits:
            for query in queries:
                try:
                    for item in reddit.subreddit(sub).search(query, limit=limit):
                        text = f"{getattr(item, 'title', '')} {getattr(item, 'selftext', '')}"
                        if not INTENT_RE.search(text):
                            continue
                        results.append({"business_name": getattr(item, "author", "reddit user") and str(item.author), "category": niche, "phone": "", "address": city, "website_url": "NONE", "website_status": "no_website", "instagram_handle": "", "facebook_page": "", "email": "", "rating": "", "review_count": "", "found_in_sources": "reddit", "explicit_website_intent": True, "notes": f"Reddit intent post: https://reddit.com{item.permalink}"})
                        if len(results) >= limit:
                            return results
                except Exception:
                    continue
        return results
