"""
main.py — Command-line lead scraper
Usage:
    python main.py --niche "interior design" --city Toronto --country Canada
"""

import argparse
import logging
import sys
import os

# Ensure the script directory is in sys.path so it can import config, scrapers, and utils correctly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scrapers import GoogleMapsScraper, InstagramScraper, YellowPagesScraper
from utils import filter_no_website, deduplicate, export_csv, export_excel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
log = logging.getLogger(__name__)


def status(msg):
    log.info(msg)


def run(niche: str, city: str, country: str, sources: list[str], max_per_source: int = 60):

    all_leads: list[dict] = []

    # ── 1. Scrape from each selected source ─────────────
    if "google_maps" in sources:
        log.info("━━ GOOGLE MAPS ━━")
        scraper = GoogleMapsScraper(headless=True)
        leads = scraper.scrape(niche, city, country, max_per_source, status)
        log.info(f"   → {len(leads)} leads from Google Maps")
        all_leads.extend(leads)

    if "instagram" in sources:
        log.info("━━ INSTAGRAM ━━")
        scraper = InstagramScraper()
        leads = scraper.scrape(niche, city, country, max_per_source, status)
        log.info(f"   → {len(leads)} leads from Instagram")
        all_leads.extend(leads)

    if "yellowpages" in sources:
        log.info("━━ YELLOW PAGES / YELP ━━")
        scraper = YellowPagesScraper()
        leads = scraper.scrape(niche, city, country, max_per_source, status)
        log.info(f"   → {len(leads)} leads from YellowPages/Yelp")
        all_leads.extend(leads)

    log.info(f"\n✅  Total raw leads: {len(all_leads)}")

    # ── 2. Deduplicate ──────────────────────────────────
    all_leads = deduplicate(all_leads)
    log.info(f"✅  After deduplication: {len(all_leads)}")

    # ── 3. Filter: keep only NO-WEBSITE businesses ──────
    no_site = filter_no_website(all_leads)
    log.info(f"🎯  Leads WITHOUT a website: {len(no_site)}")

    # ── 4. Export ────────────────────────────────────────
    csv_path = export_csv(no_site, f"leads_{city}_{niche.replace(' ','_')}.csv")
    xlsx_path = export_excel(no_site, f"leads_{city}_{niche.replace(' ','_')}.xlsx")
    log.info(f"📁  CSV  → {csv_path}")
    log.info(f"📁  XLSX → {xlsx_path}")

    return no_site


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lead Scraper")
    parser.add_argument("--niche", required=True, help='e.g. "interior design"')
    parser.add_argument("--city", required=True, help='e.g. "Toronto"')
    parser.add_argument("--country", required=True, help='e.g. "Canada"')
    parser.add_argument(
        "--sources",
        nargs="+",
        default=["google_maps", "yellowpages"],
        help="google_maps instagram yellowpages",
    )
    parser.add_argument("--max", type=int, default=60, help="Max results per source")
    args = parser.parse_args()

    run(args.niche, args.city, args.country, args.sources, args.max)
