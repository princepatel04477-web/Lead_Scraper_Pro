"""CLI entrypoint for the multi-source local lead scraper."""
from __future__ import annotations

import argparse
import logging

from lead_scraper import config
from lead_scraper.modules.directory_scraper import DirectoryScraper
from lead_scraper.modules.maps_scraper import MapsScraper
from lead_scraper.modules.reddit_finder import RedditFinder
from lead_scraper.modules.scorer import score_leads
from lead_scraper.modules.social_discovery import SocialDiscovery
from lead_scraper.modules.website_checker import annotate_websites
from lead_scraper.utils.dedupe import dedupe_leads
from lead_scraper.utils.exporter import export_leads
from lead_scraper.utils.rate_limiter import RequestLogger

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(message)s")
log = logging.getLogger(__name__)


def parse_sources(raw: str) -> list[str]:
    if not raw or raw.strip().lower() == "all":
        return list(config.DEFAULT_SOURCES)
    aliases = {"google_maps": "maps", "yellowpages": "directory", "social": "instagram"}
    sources = [aliases.get(part.strip().lower(), part.strip().lower()) for part in raw.split(",") if part.strip()]
    invalid = sorted(set(sources) - set(config.ALL_SOURCES))
    if invalid:
        raise argparse.ArgumentTypeError(f"Unsupported source(s): {', '.join(invalid)}")
    return sources


def run(niche: str, city: str, country: str = config.DEFAULT_COUNTRY, limit: int = config.DEFAULT_LIMIT, sources: list[str] | None = None, dry_run: bool = False, xlsx: bool = False) -> list[dict]:
    sources = sources or list(config.DEFAULT_SOURCES)
    logger = RequestLogger(dry_run=dry_run)
    raw: list[dict] = []

    if "maps" in sources:
        raw.extend(MapsScraper(dry_run=dry_run, request_logger=logger).scrape(niche, city, country, limit))
    if "directory" in sources:
        raw.extend(DirectoryScraper(dry_run=dry_run, request_logger=logger).scrape(niche, city, country, limit))
    if "reddit" in sources:
        raw.extend(RedditFinder(dry_run=dry_run, request_logger=logger).scrape(niche, city, country, limit))
    social = SocialDiscovery(dry_run=dry_run, request_logger=logger)
    for platform in ("instagram", "facebook", "linkedin"):
        if platform in sources:
            raw.extend(social.scrape(platform, niche, city, country, limit))

    log.info("Raw leads: %s", len(raw))
    merged = dedupe_leads(raw)
    annotate_websites(merged, dry_run=dry_run, request_logger=logger)
    scored = score_leads(merged)
    csv_path, xlsx_path = export_leads(scored, niche, city, xlsx=xlsx)
    log.info("CSV written: %s", csv_path)
    if xlsx_path:
        log.info("XLSX written: %s", xlsx_path)
    return scored


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Personal-use multi-source local lead scraper")
    parser.add_argument("--niche", required=True, help='e.g. "interior designer"')
    parser.add_argument("--city", required=True, help='e.g. "Surat"')
    parser.add_argument("--country", default=config.DEFAULT_COUNTRY, help="Default: India")
    parser.add_argument("--limit", type=int, default=config.DEFAULT_LIMIT, help="Max leads pulled per source before merge")
    parser.add_argument("--sources", type=parse_sources, default=list(config.DEFAULT_SOURCES), help="Comma list: maps,directory,reddit,instagram,facebook,linkedin. LinkedIn is opt-in only.")
    parser.add_argument("--dry-run", action="store_true", help="Log intended requests without making network calls")
    parser.add_argument("--xlsx", action="store_true", help="Also export an XLSX file")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    run(args.niche, args.city, args.country, args.limit, args.sources, args.dry_run, args.xlsx)


if __name__ == "__main__":
    main()
