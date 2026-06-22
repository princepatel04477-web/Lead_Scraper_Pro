"""Rapidfuzz-based lead deduplication and merge."""
from __future__ import annotations

import re
try:
    from rapidfuzz import fuzz
except ModuleNotFoundError:
    from difflib import SequenceMatcher
    class fuzz:
        @staticmethod
        def token_set_ratio(a, b):
            return int(SequenceMatcher(None, a, b).ratio() * 100)


def _norm(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def _phone(value: object) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _sources(lead: dict) -> set[str]:
    raw = lead.get("found_in_sources") or lead.get("source") or ""
    if isinstance(raw, (list, set, tuple)):
        return {str(x).strip().lower() for x in raw if str(x).strip()}
    return {x.strip().lower() for x in str(raw).split(",") if x.strip()}


def _is_duplicate(a: dict, b: dict) -> bool:
    pa, pb = _phone(a.get("phone")), _phone(b.get("phone"))
    if pa and pb and pa == pb:
        return True
    name_score = fuzz.token_set_ratio(_norm(a.get("business_name") or a.get("name")), _norm(b.get("business_name") or b.get("name")))
    addr_score = fuzz.token_set_ratio(_norm(a.get("address")), _norm(b.get("address"))) if a.get("address") and b.get("address") else 0
    return name_score >= 88 or (name_score >= 78 and addr_score >= 70)


def _merge(base: dict, incoming: dict) -> dict:
    merged = dict(base)
    for key, value in incoming.items():
        if value and not merged.get(key):
            merged[key] = value
    sources = _sources(base) | _sources(incoming)
    merged["found_in_sources"] = ", ".join(sorted(sources))
    notes = [str(x).strip() for x in [base.get("notes"), incoming.get("notes")] if str(x or "").strip()]
    merged["notes"] = " | ".join(dict.fromkeys(notes))
    merged["explicit_website_intent"] = bool(base.get("explicit_website_intent") or incoming.get("explicit_website_intent"))
    return merged


def dedupe_leads(leads: list[dict]) -> list[dict]:
    unique: list[dict] = []
    for lead in leads:
        normalized = dict(lead)
        normalized.setdefault("business_name", normalized.get("name", ""))
        normalized.setdefault("found_in_sources", normalized.get("source", ""))
        for idx, existing in enumerate(unique):
            if _is_duplicate(existing, normalized):
                unique[idx] = _merge(existing, normalized)
                break
        else:
            unique.append(normalized)
    return unique
