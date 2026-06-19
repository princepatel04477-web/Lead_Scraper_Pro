import logging
import requests
import re
from typing import List, Tuple, Dict, Any

logger = logging.getLogger("geo_resolver")

# Direct mapping for major global cities to countries and their business hubs/localities/districts
CITY_INTELLIGENCE: Dict[str, Dict[str, Any]] = {
    "new delhi": {
        "country": "India",
        "localities": [
            "Connaught Place", "Rohini", "Saket", "Janakpuri", "Karol Bagh", 
            "Dwarka", "Pitampura", "Lajpat Nagar", "Okhla", "Nehru Place", 
            "Vasant Kunj", "South Extension", "Greater Kailash", "Rajouri Garden", 
            "Mayur Vihar", "Chandni Chowk", "Shahdara", "Laxmi Nagar", "Paschim Vihar"
        ]
    },
    "delhi": {
        "country": "India",
        "localities": [
            "Connaught Place", "Rohini", "Saket", "Janakpuri", "Karol Bagh", 
            "Dwarka", "Pitampura", "Lajpat Nagar", "Okhla", "Nehru Place", 
            "Vasant Kunj", "South Extension", "Greater Kailash", "Rajouri Garden", 
            "Mayur Vihar", "Chandni Chowk", "Shahdara", "Laxmi Nagar", "Paschim Vihar"
        ]
    },
    "mumbai": {
        "country": "India",
        "localities": [
            "Andheri", "Bandra", "Colaba", "Juhu", "Dadar", "Worli", "Borivali", 
            "Chembur", "Powai", "Thane", "Navi Mumbai", "Malad", "Kurla", 
            "Ghatkopar", "Nariman Point", "Lower Parel"
        ]
    },
    "bangalore": {
        "country": "India",
        "localities": [
            "Koramangala", "Indiranagar", "Jayanagar", "Whitefield", "HSR Layout", 
            "Electronic City", "Malleshwaram", "Banashankari", "Rajajinagar", 
            "Marathahalli", "Bellandur", "Hebbal", "Jalahalli"
        ]
    },
    "bengaluru": {
        "country": "India",
        "localities": [
            "Koramangala", "Indiranagar", "Jayanagar", "Whitefield", "HSR Layout", 
            "Electronic City", "Malleshwaram", "Banashankari", "Rajajinagar", 
            "Marathahalli", "Bellandur", "Hebbal", "Jalahalli"
        ]
    },
    "london": {
        "country": "United Kingdom",
        "localities": [
            "Westminster", "City of London", "Canary Wharf", "Camden", "Kensington", 
            "Chelsea", "Soho", "Greenwich", "Shoreditch", "Islington", "Hackney", 
            "Brixton", "Croydon", "Wembley", "Stratford", "Richmond"
        ]
    },
    "berlin": {
        "country": "Germany",
        "localities": [
            "Mitte", "Kreuzberg", "Prenzlauer Berg", "Charlottenburg", "Friedrichshain", 
            "Neukölln", "Schöneberg", "Wilmersdorf", "Tempelhof", "Pankow", "Spandau"
        ]
    },
    "dubai": {
        "country": "UAE",
        "localities": [
            "Downtown Dubai", "Dubai Marina", "Jumeirah", "Deira", "Bur Dubai", 
            "Business Bay", "Al Barsha", "JLT", "Karama", "Silicon Oasis", "Palm Jumeirah"
        ]
    },
    "new york": {
        "country": "United States",
        "localities": [
            "Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island", "Midtown", 
            "Soho", "Chelsea", "Williamsburg", "Astoria", "Flushing", "Harlem", 
            "DUMBO", "Long Island City", "Tribeca", "Greenwich Village"
        ]
    },
    "nyc": {
        "country": "United States",
        "localities": [
            "Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island", "Midtown", 
            "Soho", "Chelsea", "Williamsburg", "Astoria", "Flushing", "Harlem", 
            "DUMBO", "Long Island City"
        ]
    },
    "los angeles": {
        "country": "United States",
        "localities": [
            "Downtown LA", "Hollywood", "Santa Monica", "Beverly Hills", "Pasadena", 
            "Venice", "Glendale", "Long Beach", "Sherman Oaks", "Westwood", "Silver Lake"
        ]
    },
    "chicago": {
        "country": "United States",
        "localities": [
            "Loop", "Lincoln Park", "Wicker Park", "Lakeview", "River North", 
            "West Loop", "Hyde Park", "Logan Square", "Bucktown", "Gold Coast"
        ]
    },
    "toronto": {
        "country": "Canada",
        "localities": [
            "Downtown Toronto", "Scarborough", "North York", "Etobicoke", "Mississauga", 
            "Brampton", "Vaughan", "Markham", "Richmond Hill", "Yorkville", "The Annex"
        ]
    },
    "sydney": {
        "country": "Australia",
        "localities": [
            "Sydney CBD", "Darlinghurst", "Surry Hills", "Newtown", "Bondi", 
            "Parramatta", "Chatswood", "Manly", "Pyrmont", "Alexandria", "Paddington"
        ]
    },
    "paris": {
        "country": "France",
        "localities": [
            "Le Marais", "Montmartre", "Latin Quarter", "Champs-Élysées", "Belleville", 
            "Bastille", "Saint-Germain-des-Prés", "La Défense", "Montparnasse", "Pigalle"
        ]
    },
    "tokyo": {
        "country": "Japan",
        "localities": [
            "Shinjuku", "Shibuya", "Ginza", "Roppongi", "Akihabara", "Asakusa", 
            "Chiyoda", "Minato", "Ikebukuro", "Ueno", "Harajuku", "Ebisu"
        ]
    },
    "singapore": {
        "country": "Singapore",
        "localities": [
            "Orchard Road", "Marina Bay", "Jurong", "Tampines", "Woodlands", 
            "Bugis", "Chinatown", "Clarke Quay", "Sentosa", "Little India"
        ]
    },
    "san francisco": {
        "country": "United States",
        "localities": [
            "SOMA", "Mission District", "Financial District", "Marina District", 
            "North Beach", "Castro", "Haight-Ashbury", "Pacific Heights", "Noe Valley"
        ]
    },
    "seattle": {
        "country": "United States",
        "localities": [
            "Capitol Hill", "Ballard", "Fremont", "Downtown Seattle", "Queen Anne", 
            "South Lake Union", "University District", "Pioneer Square"
        ]
    },
    "austin": {
        "country": "United States",
        "localities": [
            "Downtown Austin", "South Congress", "East Austin", "North Loop", 
            "West Lake Hills", "Domain", "Rainey Street"
        ]
    },
    "boston": {
        "country": "United States",
        "localities": [
            "Back Bay", "Beacon Hill", "South End", "North End", "Seaport District", 
            "Cambridge", "Allston", "Fenway"
        ]
    },
    "miami": {
        "country": "United States",
        "localities": [
            "South Beach", "Brickell", "Wynwood", "Little Havana", "Coconut Grove", 
            "Coral Gables", "Downtown Miami", "Design District"
        ]
    }
}

def resolve_country(city: str) -> str:
    """
    Attempts to resolve country for a given city name.
    Uses local CITY_INTELLIGENCE mapping first, then falls back to OpenStreetMap Nominatim API.
    """
    city_clean = city.strip().lower()
    
    # 1. Local Lookup
    if city_clean in CITY_INTELLIGENCE:
        country = CITY_INTELLIGENCE[city_clean]["country"]
        logger.info(f"Resolved country locally: {city} -> {country}")
        return country
        
    # Check if city name is contained in the keys (e.g. "new delhi, india" -> "new delhi")
    for key, val in CITY_INTELLIGENCE.items():
        if key in city_clean:
            logger.info(f"Resolved country locally (partial match): {city} -> {val['country']}")
            return val["country"]

    # 2. Remote Lookup (OpenStreetMap Nominatim)
    try:
        url = f"https://nominatim.openstreetmap.org/search?city={requests.utils.quote(city)}&format=json&addressdetails=1&limit=1"
        headers = {"User-Agent": "AntigravityLeadScraper/1.0 (Google Partner Pair Programming)"}
        response = requests.get(url, headers=headers, timeout=2.5)
        if response.status_code == 200:
            data = response.json()
            if data and isinstance(data, list) and len(data) > 0:
                address = data[0].get("address", {})
                country = address.get("country", "")
                if country:
                    logger.info(f"Resolved country via Nominatim API: {city} -> {country}")
                    return country
    except Exception as e:
        logger.warning(f"OSM Nominatim resolution failed for {city}: {e}")

    # 3. Fail-safe Fallback (Default to empty, or try regex search)
    logger.warning(f"Could not resolve country for city '{city}'. Returning empty string.")
    return ""

def get_city_localities(city: str) -> List[str]:
    """
    Returns list of localities/business hubs/commercial zones for a city.
    Uses local CITY_INTELLIGENCE mapping, or fallback sub-areas.
    """
    city_clean = city.strip().lower()
    
    if city_clean in CITY_INTELLIGENCE:
        return CITY_INTELLIGENCE[city_clean]["localities"]
        
    for key, val in CITY_INTELLIGENCE.items():
        if key in city_clean:
            return val["localities"]
            
    # Remote Lookup fallback for localities (finding suburbs or neighborhoods)
    try:
        url = f"https://nominatim.openstreetmap.org/search?q=suburb+in+{requests.utils.quote(city)}&format=json&limit=15"
        headers = {"User-Agent": "AntigravityLeadScraper/1.0 (Google Partner Pair Programming)"}
        response = requests.get(url, headers=headers, timeout=2.5)
        if response.status_code == 200:
            data = response.json()
            if data and isinstance(data, list) and len(data) > 0:
                suburbs = []
                for item in data:
                    name = item.get("display_name", "").split(",")[0].strip()
                    if name and name.lower() not in city_clean and name not in suburbs:
                        suburbs.append(name)
                if len(suburbs) > 3:
                    logger.info(f"Resolved {len(suburbs)} localities via Nominatim API for {city}")
                    return suburbs
    except Exception as e:
        logger.warning(f"OSM Nominatim localities fetch failed for {city}: {e}")

    # Fallback default sectors if city not found
    return [
        "Downtown", "Commercial Area", "Business District", "Industrial Zone",
        "Market Center", "Central Plaza", "Retail Park", "Financial Center"
    ]
