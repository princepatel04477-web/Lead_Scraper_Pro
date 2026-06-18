import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from scrapers import GoogleMapsScraper, InstagramScraper, YellowPagesScraper, FacebookScraper
    print("SUCCESS: All scrapers successfully imported!")
except Exception as e:
    print(f"FAILED: Import error: {e}")
    sys.exit(1)
