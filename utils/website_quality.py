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
        Determines the website quality score (0-100), Tier (A-E), Health,
        Upgrade Opportunity, Business Maturity, and Recommended Priority.
        """
        if not lead_data:
            lead_data = {}

        # Default fallback structure
        result = {
            "website_exists": False,
            "website_score": 0,
            "website_tier": "No Website",
            "website_health": "None",
            "upgrade_opportunity": "None",
            "business_maturity": "Struggling",
            "recommended_priority": "Low",
            "website_checks": {}
        }

        if not url or not url.strip():
            result["upgrade_opportunity"] = "High" if (lead_data.get("phone") or lead_data.get("email")) else "Medium"
            result["recommended_priority"] = "High" if result["upgrade_opportunity"] == "High" else "Medium"
            return result

        url = url.strip()
        url_lower = url.lower()

        # Check for Social profile only
        is_social = any(domain in url_lower for domain in SOCIAL_DOMAINS)
        if is_social:
            result["upgrade_opportunity"] = "High" if (lead_data.get("phone") or lead_data.get("email")) else "Medium"
            result["recommended_priority"] = "High" if result["upgrade_opportunity"] == "High" else "Medium"
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
                result["upgrade_opportunity"] = "High"
                result["recommended_priority"] = "High"
                return result
                
        except (requests.exceptions.RequestException, Exception) as e:
            logger.debug(f"Connection failure for {target_url}: {e}")
            result["upgrade_opportunity"] = "High"
            result["recommended_priority"] = "High"
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
            result["upgrade_opportunity"] = "High"
            result["recommended_priority"] = "High"
            return result

        # Check for Dead Website (Placeholder, under construction, coming soon)
        is_dead = any(kw in page_text for kw in UNDER_CONSTRUCTION_KEYWORDS)
        html_len = len(html_content.strip())
        text_len = len(page_text.strip())
        
        # Missing stylesheet/CSS layout check
        css_links = soup.find_all("link", rel="stylesheet")
        inline_styles = soup.find_all("style")
        missing_css = (len(css_links) == 0 and len(inline_styles) == 0)

        if is_dead or html_len < 400 or text_len < 100 or missing_css:
            result["website_score"] = 15
            result["website_tier"] = "Dead Website"
            result["website_health"] = "Broken"
            result["upgrade_opportunity"] = "High"
            result["business_maturity"] = "Struggling"
            result["recommended_priority"] = "High"
            result["website_checks"] = {
                "ssl": target_url.startswith("https://") or response.url.startswith("https://"),
                "responsive": False,
                "speed": False,
                "contact": False,
                "about": False,
                "services": False,
                "team": False,
                "portfolio": False,
                "testimonials": False,
                "careers": False,
                "blog": False,
                "multiple_contacts": False
            }
            return result

        # Calculate Technical Checks
        score = 0
        checks = {}

        # 1. SSL (+10)
        ssl_secure = target_url.startswith("https://") or response.url.startswith("https://")
        if ssl_secure:
            score += 10
        checks["ssl"] = ssl_secure

        # 2. Mobile Responsive (+15)
        viewport_meta = soup.find("meta", attrs={"name": "viewport"})
        responsive = viewport_meta is not None
        if responsive:
            score += 15
        checks["responsive"] = responsive

        # 3. Page Speed / Latency (+15)
        # Latency < 0.8s = +15, < 1.5s = +10, < 3.0s = +5
        speed_score = 0
        if latency < 0.8:
            speed_score = 15
        elif latency < 1.5:
            speed_score = 10
        elif latency < 3.0:
            speed_score = 5
        score += speed_score
        checks["speed"] = (speed_score >= 10)

        # Scrape all link anchors for structure analysis
        links = []
        for a in soup.find_all("a", href=True):
            links.append((a.get_text().lower(), a["href"].lower()))

        def has_link(keywords):
            for anchor_text, href in links:
                if any(kw in href or kw in anchor_text for kw in keywords):
                    return True
            return False

        # 4. Contact Page (+10)
        has_contact = has_link(["contact", "get-in-touch", "reach-us", "find-us"])
        if has_contact or "contact us" in page_text:
            score += 10
        checks["contact"] = has_contact

        # 5. About Page (+5)
        has_about = has_link(["about", "who-we-are", "our-story", "about-us"])
        if has_about or "about us" in page_text:
            score += 5
        checks["about"] = has_about

        # 6. Service Pages (+10)
        has_services = has_link(["services", "what-we-do", "products", "solutions", "our-work"])
        if has_services or "our services" in page_text:
            score += 10
        checks["services"] = has_services

        # 7. Team Page (+5)
        has_team = has_link(["team", "meet-the-team", "leadership", "staff", "management"])
        if has_team or "meet the team" in page_text:
            score += 5
        checks["team"] = has_team

        # 8. Portfolio (+10)
        has_portfolio = has_link(["portfolio", "gallery", "projects", "showcase", "case-studies"])
        if has_portfolio or "our portfolio" in page_text:
            score += 10
        checks["portfolio"] = has_portfolio

        # 9. Testimonials (+5)
        has_testimonials = has_link(["testimonials", "reviews", "feedback", "what-they-say"])
        if has_testimonials or "testimonials" in page_text or "what clients say" in page_text:
            score += 5
        checks["testimonials"] = has_testimonials

        # 10. Careers Page (+5)
        has_careers = has_link(["careers", "jobs", "join-us", "employment"])
        if has_careers or "careers" in page_text or "join our team" in page_text:
            score += 5
        checks["careers"] = has_careers

        # 11. Blog/Insights (+5)
        has_blog = has_link(["blog", "news", "insights", "articles", "newsletters"])
        if has_blog or "blog" in page_text or "latest news" in page_text:
            score += 5
        checks["blog"] = has_blog

        # 12. Multiple Contact Methods (+10)
        # Search page text for phone numbers and email links
        has_email_anchor = has_link(["mailto:"])
        has_tel_anchor = has_link(["tel:"])
        
        # Text search fallback using regex
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', page_text)
        phones = re.findall(r'\+?\d[\d -]{8,15}\d', page_text)
        
        has_multiple = (has_email_anchor or len(emails) > 0) and (has_tel_anchor or len(phones) > 0)
        if has_multiple:
            score += 10
        checks["multiple_contacts"] = has_multiple

        # Set final score and breakdown
        result["website_score"] = min(max(score, 1), 100)
        
        # Classify Tier
        if result["website_score"] <= 20:
            result["website_tier"] = "Dead Website"
            result["website_health"] = "Broken"
        elif result["website_score"] <= 50:
            result["website_tier"] = "Weak Website"
            result["website_health"] = "Substandard"
        elif result["website_score"] <= 80:
            result["website_tier"] = "Good Website"
            result["website_health"] = "Healthy"
        else:
            result["website_tier"] = "Exceptional Website"
            result["website_health"] = "Excellent"

        # Determine Lead Opportunity
        # Active business indicator
        has_phone = lead_data.get("phone") or len(phones) > 0
        has_email = lead_data.get("email") or len(emails) > 0
        has_social = lead_data.get("social") or is_social
        has_rating = lead_data.get("score") or lead_data.get("rating")
        is_active_business = (has_phone or has_email or has_social or has_rating)

        if result["website_score"] < 50 and is_active_business:
            result["upgrade_opportunity"] = "High"
        elif result["website_score"] < 80:
            result["upgrade_opportunity"] = "Medium"
        else:
            result["upgrade_opportunity"] = "Low"

        # Determine Business Maturity
        # High value client check: Score > 80 AND established indicators
        has_locations_indicator = "locations" in page_text or "offices" in page_text or "headquarters" in page_text
        has_large_team = has_team or "leadership team" in page_text
        has_active_marketing = has_blog and (is_social or "newsletter" in page_text)
        
        is_premium_client = result["website_score"] > 80 and (has_locations_indicator or has_large_team or has_careers or has_active_marketing)
        
        if is_premium_client:
            result["business_maturity"] = "Established"
            result["upgrade_opportunity"] = "High Value Client" # Custom tag as requested
        elif result["website_score"] > 80:
            result["business_maturity"] = "Mature"
        elif result["website_score"] >= 51:
            result["business_maturity"] = "Growing"
        elif result["website_score"] >= 21:
            result["business_maturity"] = "Early"
        else:
            result["business_maturity"] = "Struggling"

        # Map Recommended Priority
        if result["upgrade_opportunity"] == "High" and (lead_data.get("phone") or lead_data.get("email")):
            result["recommended_priority"] = "Critical"
        elif result["upgrade_opportunity"] == "High" or result["upgrade_opportunity"] == "High Value Client":
            result["recommended_priority"] = "High"
        elif result["upgrade_opportunity"] == "Medium":
            result["recommended_priority"] = "Medium"
        else:
            result["recommended_priority"] = "Low"

        result["website_checks"] = checks
        return result
