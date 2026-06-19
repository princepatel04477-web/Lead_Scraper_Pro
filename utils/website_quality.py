import re
import time
import logging
import urllib.parse
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("website_quality")

SOCIAL_DOMAINS = [
    "facebook.com", "instagram.com", "linkedin.com", "twitter.com", "x.com",
    "pinterest.com", "youtube.com", "linktr.ee", "yelp.com", "tripadvisor.com"
]

PARKED_KEYWORDS = [
    "domain expired", "expired domain", "this domain is parked", "domain is for sale",
    "buy this domain", "domain registration expired", "parking page", "parked free",
    "hugedomains", "sedo.com", "dan.com", "domainname", "domain is available"
]

UNDER_CONSTRUCTION_KEYWORDS = [
    "under construction", "coming soon", "site is coming", "stay tuned", "launching soon",
    "we are preparing", "placeholder template"
]

class WebsiteQualityIntelligenceSystem:
    def __init__(self):
        pass

    def evaluate_website(self, url: str, lead_data: dict = None) -> dict:
        """
        Evaluates website quality, calculates the Website Opportunity Score (0-100)
        and classifies it into Tiers A-E.
        """
        if not lead_data:
            lead_data = {}

        # Default fallback structure for no website
        result = {
            "website_exists": False,
            "website_score": 0,  # Legacy field
            "website_opportunity_score": 100,  # Website Opportunity Score (0-100)
            "website_tier": "Tier E",  # Tier E: No Website
            "website_health": "None",
            "upgrade_opportunity": "High",
            "business_maturity": "Struggling",
            "recommended_priority": "Critical" if (lead_data.get("phone") or lead_data.get("email")) else "High",
            "website_checks": {
                "ssl": False,
                "responsive": False,
                "contact": False,
                "seo": False,
                "outdated": True,
                "social": False,
                "branding": False
            }
        }

        if not url or not url.strip():
            return result

        url = url.strip()
        url_lower = url.lower()

        # Check for Social profile only
        is_social = any(domain in url_lower for domain in SOCIAL_DOMAINS)
        if is_social:
            # Treats social profile as having "No Website" for opportunity discovery
            result["website_exists"] = False
            result["website_opportunity_score"] = 100
            result["website_tier"] = "Tier E"
            return result

        # Ensure correct prefix
        target_url = url
        if not target_url.startswith("http"):
            target_url = "http://" + target_url

        try:
            start_time = time.time()
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            response = requests.get(target_url, timeout=3.5, headers=headers, allow_redirects=True)
            latency = time.time() - start_time
            
            if response.status_code >= 400:
                result["website_exists"] = True
                result["website_opportunity_score"] = 90  # High opportunity
                result["website_tier"] = "Tier D"  # Dead website
                result["website_health"] = "Broken"
                result["website_checks"]["ssl"] = target_url.startswith("https://")
                return result
                
        except (requests.exceptions.RequestException, Exception) as e:
            logger.debug(f"Connection failure for {target_url}: {e}")
            result["website_exists"] = True
            result["website_opportunity_score"] = 95  # Connection error / dead website
            result["website_tier"] = "Tier D"  # Dead Website
            result["website_health"] = "Broken"
            result["website_checks"]["ssl"] = target_url.startswith("https://")
            return result

        # Page loaded successfully!
        result["website_exists"] = True
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')
        page_text = soup.get_text().lower()

        # Check for Parked/For Sale Domain
        is_parked = any(kw in page_text for kw in PARKED_KEYWORDS)
        if is_parked:
            result["website_exists"] = False
            result["website_opportunity_score"] = 100
            result["website_tier"] = "Tier E"  # No website
            return result

        # Check for Dead Website (Placeholder, under construction, coming soon)
        is_under_construction = any(kw in page_text for kw in UNDER_CONSTRUCTION_KEYWORDS)
        html_len = len(html_content.strip())
        text_len = len(page_text.strip())
        
        # Missing stylesheet/CSS layout check
        css_links = soup.find_all("link", rel="stylesheet")
        inline_styles = soup.find_all("style")
        missing_css = (len(css_links) == 0 and len(inline_styles) == 0)

        if is_under_construction or html_len < 400 or text_len < 100 or missing_css:
            result["website_opportunity_score"] = 90
            result["website_tier"] = "Tier D"  # Dead Website
            result["website_health"] = "Broken"
            result["website_checks"] = {
                "ssl": target_url.startswith("https://") or response.url.startswith("https://"),
                "responsive": False,
                "contact": False,
                "seo": False,
                "outdated": True,
                "social": False,
                "branding": False
            }
            return result

        # Evaluate specific checks
        checks = {}

        # 1. SSL
        ssl_secure = target_url.startswith("https://") or response.url.startswith("https://")
        checks["ssl"] = ssl_secure

        # 2. Mobile Responsive (viewport check)
        viewport_meta = soup.find("meta", attrs={"name": "viewport"})
        responsive = viewport_meta is not None
        checks["responsive"] = responsive

        # 3. Contact Form / Channels
        links = []
        for a in soup.find_all("a", href=True):
            links.append((a.get_text().lower(), a["href"].lower()))

        def has_link(keywords):
            for anchor_text, href in links:
                if any(kw in href or kw in anchor_text for kw in keywords):
                    return True
            return False

        has_contact = has_link(["contact", "get-in-touch", "reach-us", "find-us"]) or "contact us" in page_text or soup.find("form") is not None
        checks["contact"] = has_contact

        # 4. SEO Structure (Check for meta title, description, and h1 tags)
        has_title = soup.title is not None and len(soup.title.get_text().strip()) > 0
        has_desc = soup.find("meta", attrs={"name": "description"}) is not None
        has_h1 = soup.find("h1") is not None
        seo_structure = has_title and has_desc and has_h1
        checks["seo"] = seo_structure

        # 5. Outdated Design
        # Checks if it uses outdated layouts (e.g. table-based layouts without modern divs)
        # or has deprecated tags, or lacks modern tags like <header>, <nav>, <footer>
        has_modern_tags = (soup.find("header") or soup.find("nav") or soup.find("footer")) is not None
        has_table_layout = len(soup.find_all("table")) > 2 and len(soup.find_all("div")) < 5
        outdated = (not has_modern_tags) or has_table_layout or (latency > 3.0) or (html_len > 5000 and len(css_links) == 0)
        checks["outdated"] = outdated

        # 6. Social Links
        has_social = any(any(domain in href for domain in ["facebook.com", "instagram.com", "twitter.com", "x.com", "linkedin.com", "youtube.com"]) for _, href in links)
        checks["social"] = has_social

        # 7. Branding (Logo or favicon check)
        has_favicon = soup.find("link", rel=re.compile(r"icon", re.I)) is not None
        has_logo = any("logo" in img.get("src", "").lower() or "logo" in img.get("alt", "").lower() for img in soup.find_all("img"))
        branding = has_favicon or has_logo
        checks["branding"] = branding

        # OPPORTUNITY SCORE CALCULATION
        # Baseline check: is it generally a Poor website?
        # We classify a website as poor if it fails multiple checks (responsive, SSL, SEO, etc.)
        failed_count = sum(1 for k, v in checks.items() if not v and k != "outdated") + (1 if checks["outdated"] else 0)
        is_poor_website = failed_count >= 3

        opp_score = 0
        if is_poor_website:
            opp_score += 35  # Poor Website baseline

        if not checks["ssl"]: opp_score += 10
        if not checks["responsive"]: opp_score += 15
        if not checks["contact"]: opp_score += 10
        if not checks["seo"]: opp_score += 10
        if checks["outdated"]: opp_score += 15
        if not checks["social"]: opp_score += 5
        if not checks["branding"]: opp_score += 10

        opp_score = min(max(opp_score, 0), 100)
        result["website_opportunity_score"] = opp_score

        # CLASSIFICATION TIER
        if opp_score >= 60:
            result["website_tier"] = "Tier C"  # Poor Website
            result["website_health"] = "Substandard"
            result["upgrade_opportunity"] = "High"
            result["recommended_priority"] = "High"
        elif opp_score >= 25:
            result["website_tier"] = "Tier B"  # Good Website
            result["website_health"] = "Healthy"
            result["upgrade_opportunity"] = "Medium"
            result["recommended_priority"] = "Medium"
        else:
            result["website_tier"] = "Tier A"  # Exceptional Website
            result["website_health"] = "Excellent"
            result["upgrade_opportunity"] = "Low"
            result["recommended_priority"] = "Low"

        # Backwards compatibility
        result["website_score"] = 100 - opp_score

        # Extra contact details parsing
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', page_text)
        phones = re.findall(r'\+?\d[\d -]{8,15}\d', page_text)
        if not lead_data.get("email") and len(emails) > 0:
            result["email"] = emails[0]
        if not lead_data.get("phone") and len(phones) > 0:
            result["phone"] = phones[0]

        result["website_checks"] = checks
        return result
