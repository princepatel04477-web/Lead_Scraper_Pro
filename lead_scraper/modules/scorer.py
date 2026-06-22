"""Lead scoring according to the build prompt."""
from __future__ import annotations


def _review_count(lead: dict) -> int:
    raw = lead.get("review_count", lead.get("reviews", 0))
    try:
        return int(str(raw or "0").replace(",", ""))
    except ValueError:
        return 0


def score_lead(lead: dict) -> dict:
    score = 0
    status = lead.get("website_status") or "no_website"
    if status == "no_website":
        score += 40
    elif status == "outdated":
        score += 15
    sources = [s.strip() for s in str(lead.get("found_in_sources") or lead.get("source") or "").split(",") if s.strip()]
    if len(set(sources)) >= 2:
        score += 10
    reviews = _review_count(lead)
    if reviews > 50:
        score += 15
    elif 10 <= reviews <= 50:
        score += 8
    if lead.get("phone"):
        score += 5
    lead["lead_score"] = min(score, 100)
    if lead.get("explicit_website_intent"):
        lead["lead_priority"] = "🔥 Hot"
    elif lead["lead_score"] >= 80:
        lead["lead_priority"] = "🔥 Hot"
    elif lead["lead_score"] >= 50:
        lead["lead_priority"] = "🟡 Warm"
    else:
        lead["lead_priority"] = "⚪ Cold"
    return lead


def score_leads(leads: list[dict]) -> list[dict]:
    return sorted((score_lead(lead) for lead in leads), key=lambda x: x.get("lead_score", 0), reverse=True)
