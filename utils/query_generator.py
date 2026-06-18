"""
Query Generator for Advanced Search Intelligence Expansion
──────────────────────────────────────────────────────────
Generates semantic, business-type, commercial intent, and service variations.
"""

import logging

logger = logging.getLogger(__name__)

# Lookup table for synonyms and related service/industry terminology
NICHE_SYNONYMS = {
    "interior design": [
        "interior designer",
        "home decorator",
        "interior decoration",
        "space planner",
        "home stager",
        "kitchen design",
        "bathroom remodeler",
        "office interior design"
    ],
    "dentist": [
        "dental clinic",
        "dental office",
        "orthodontist",
        "dental care",
        "cosmetic dentist",
        "teeth whitening",
        "family dentistry"
    ],
    "plumber": [
        "plumbing services",
        "emergency plumber",
        "drain cleaning",
        "pipe repair",
        "heating contractor",
        "leak detection"
    ],
    "marketing": [
        "marketing agency",
        "digital marketing",
        "advertising agency",
        "seo agency",
        "social media marketing",
        "pr agency",
        "creative agency"
    ],
    "real estate": [
        "real estate agency",
        "realtor",
        "property management",
        "real estate broker",
        "home selling"
    ],
    "restaurant": [
        "cafe",
        "diner",
        "bistro",
        "eatery",
        "food delivery",
        "grill",
        "pub",
        "pizzeria"
    ],
    "gym": [
        "fitness center",
        "personal trainer",
        "health club",
        "yoga studio",
        "crossfit gym",
        "fitness studio"
    ],
    "bakery": [
        "cake shop",
        "pastry shop",
        "baker",
        "bread shop",
        "patisserie"
    ],
    "accounting": [
        "accountant",
        "cpa",
        "tax preparation",
        "bookkeeping",
        "financial planner",
        "tax advisor"
    ],
    "architect": [
        "architectural firm",
        "space planning consultant",
        "home design studio",
        "landscape architect",
        "building designer"
    ],
    "lawyer": [
        "law firm",
        "attorney",
        "legal counsel",
        "notary public",
        "solicitor"
    ],
    "cleaning": [
        "cleaning service",
        "house keeping",
        "maid service",
        "commercial cleaner",
        "window washing"
    ],
    "construction": [
        "builder",
        "general contractor",
        "renovation contractor",
        "home remodeler",
        "roofing contractor",
        "home improvement"
    ],
    "photography": [
        "wedding photographer",
        "headshot studio",
        "portrait photography",
        "video production"
    ]
}

BUSINESS_TYPES = [
    "company",
    "firm",
    "agency",
    "studio",
    "provider",
    "consultant",
    "enterprise",
    "solutions"
]

COMMERCIAL_INTENT = [
    "contact",
    "office",
    "about",
    "team"
]


def generate_google_maps_queries(niche: str, city: str, country: str, broaden: bool = False) -> list[str]:
    """
    Generate expanded list of search queries for Google Maps.
    """
    niche_lower = niche.lower().strip()
    queries = []

    # 1. Base Query
    queries.append(f"{niche} in {city} {country}")

    # 2. Semantic & Service Expansion
    syns = [niche]
    for key, val in NICHE_SYNONYMS.items():
        if key in niche_lower or niche_lower in key:
            syns.extend(val)
            break

    # General fallback if no synonyms in dictionary
    if len(syns) == 1:
        syns.append(f"{niche} services")
        syns.append(f"{niche} specialist")

    for syn in syns[:4]:  # Top 4 semantic variations
        q = f"{syn} in {city} {country}"
        if q not in queries:
            queries.append(q)

    # 3. Business Type Expansion
    for b_type in BUSINESS_TYPES[:3]:
        q = f"{niche} {b_type} in {city}"
        if q not in queries:
            queries.append(q)

    # 4. Broaden Search / Geographic Expansion
    if broaden:
        queries.append(f"{niche} near {city}")
        queries.append(f"{niche} {city}")
        # Add a surrounding district format
        queries.append(f"{niche} in {city} downtown")

    logger.info(f"Generated {len(queries)} Google Maps queries for '{niche}' in '{city}'.")
    return queries


def generate_facebook_queries(niche: str, city: str, country: str) -> list[str]:
    """
    Generate expanded list of dorking search queries for Facebook pages.
    """
    niche_lower = niche.lower().strip()
    queries = []

    # 1. Base Google Dorking
    queries.append(f"site:facebook.com {niche} in {city} {country}")

    # 2. Semantic & Service expansions
    syns = [niche]
    for key, val in NICHE_SYNONYMS.items():
        if key in niche_lower or niche_lower in key:
            syns.extend(val)
            break

    if len(syns) == 1:
        syns.append(f"{niche} services")

    for syn in syns[:3]:
        q = f"site:facebook.com {syn} in {city}"
        if q not in queries:
            queries.append(q)

    # 3. Commercial Intent & Business Type Expansions
    queries.append(f"site:facebook.com {niche} {city} contact")
    queries.append(f"site:facebook.com {niche} near {city}")

    for b_type in BUSINESS_TYPES[:2]:
        q = f"site:facebook.com {niche} {b_type} in {city}"
        if q not in queries:
            queries.append(q)

    logger.info(f"Generated {len(queries)} Facebook Google dorking queries for '{niche}' in '{city}'.")
    return queries
