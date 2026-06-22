# Lead Scraper Pro — Local CLI

Personal-use, zero-cost Python CLI for finding local businesses that may need a website or redesign.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

## Usage

```bash
python main.py --niche "interior designer" --city "Surat" --country "India" \
  --limit 50 --sources maps,directory,reddit,instagram,facebook
```

Options:
- `--niche` and `--city` are required.
- `--country` defaults to `India`.
- `--limit` defaults to `50` per source before merge.
- `--sources` is a comma list of `maps,directory,reddit,instagram,facebook,linkedin`; LinkedIn is opt-in only.
- `--dry-run` logs planned requests and makes zero network calls.
- `--xlsx` writes an additional Excel file.

Outputs are written to `output/leads_{niche}_{city}_{date}.csv` and optionally `.xlsx`.

## Reddit API

Reddit search uses the official API through PRAW. Create a free script app at <https://www.reddit.com/prefs/apps> and set:

```bash
export REDDIT_CLIENT_ID="..."
export REDDIT_CLIENT_SECRET="..."
export REDDIT_USER_AGENT="lead-scraper-pro/1.0 by your_reddit_username"
```

If credentials are missing, the Reddit module skips safely.

## Compliance guardrails

- Collect only public business contact information.
- Stop gracefully on CAPTCHA, unusual-traffic, or block signals.
- Reddit uses PRAW only; no Reddit HTML scraping.
- Instagram, Facebook, and LinkedIn are discovered from public search-result snippets only; no login automation or platform page scraping.
- Use `--dry-run` to inspect all planned requests before a live run.
