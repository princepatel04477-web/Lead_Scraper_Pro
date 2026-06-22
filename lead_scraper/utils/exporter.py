"""CSV/XLSX exporter for the requested schema."""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path
import csv

from lead_scraper import config

COLUMNS = ["business_name", "category", "phone", "address", "website_url", "website_status", "instagram_handle", "facebook_page", "email", "rating", "review_count", "found_in_sources", "lead_score", "lead_priority", "notes"]


def safe_slug(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    return value or "leads"


def normalize_for_export(lead: dict) -> dict:
    return {
        "business_name": lead.get("business_name") or lead.get("name") or "",
        "category": lead.get("category", ""),
        "phone": lead.get("phone", ""),
        "address": lead.get("address", ""),
        "website_url": lead.get("website_url") or lead.get("website") or "NONE",
        "website_status": lead.get("website_status", "no_website"),
        "instagram_handle": lead.get("instagram_handle") or lead.get("instagram") or "",
        "facebook_page": lead.get("facebook_page", ""),
        "email": lead.get("email", ""),
        "rating": lead.get("rating", ""),
        "review_count": lead.get("review_count") or lead.get("reviews") or "",
        "found_in_sources": lead.get("found_in_sources") or lead.get("source") or "",
        "lead_score": lead.get("lead_score", 0),
        "lead_priority": lead.get("lead_priority", "⚪ Cold"),
        "notes": lead.get("notes", ""),
    }


def export_leads(leads: list[dict], niche: str, city: str, xlsx: bool = False) -> tuple[Path, Path | None]:
    base = f"leads_{safe_slug(niche)}_{safe_slug(city)}_{date.today().isoformat()}"
    rows = [normalize_for_export(lead) for lead in leads]
    csv_path = config.OUTPUT_DIR / f"{base}.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    xlsx_path = None
    if xlsx:
        xlsx_path = config.OUTPUT_DIR / f"{base}.xlsx"
        try:
            from openpyxl import Workbook
            wb = Workbook()
            ws = wb.active
            ws.title = "Leads"
            ws.append(COLUMNS)
            for row in rows:
                ws.append([row.get(col, "") for col in COLUMNS])
            wb.save(xlsx_path)
        except ModuleNotFoundError:
            xlsx_path = None
    return csv_path, xlsx_path
