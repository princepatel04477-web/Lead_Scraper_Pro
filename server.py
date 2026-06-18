import os
import sys
import uuid
import json
import logging
import threading
import queue
from typing import List, Dict, Any
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Ensure script directory is in sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scrapers import GoogleMapsScraper, InstagramScraper, YellowPagesScraper, FacebookScraper
from utils.filters import filter_no_website, deduplicate
from utils.export import export_csv, export_excel

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("server")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global memory state
active_scan = {
    "task_id": None,
    "state": "IDLE", # IDLE, ACTIVE, COMPLETED, ERROR
    "niche": "",
    "city": "",
    "country": "",
    "entities_discovered": 0,
    "contacts_verified": 0,
    "logs": [],
    "leads": [],
    "latency": 24,
}

# Queue for SSE streaming
stream_queues = []
lock = threading.Lock()

class SearchRequest(BaseModel):
    niche: str
    city: str
    country: str
    sources: List[str] = ["google_maps", "yellowpages"]
    max_results: int = 50
    broaden: bool = True
    headless: bool = True

def add_log(msg: str, is_success: bool = False):
    with lock:
        log_entry = {"time": len(active_scan["logs"]), "message": msg, "is_success": is_success}
        active_scan["logs"].append(log_entry)
        
        # Dispatch to all connected SSE clients
        event_data = {
            "type": "log",
            "data": log_entry,
            "stats": {
                "entities": active_scan["entities_discovered"],
                "contacts": active_scan["contacts_verified"],
                "state": active_scan["state"]
            }
        }
        for q in list(stream_queues):
            try:
                q.put_nowait(event_data)
            except Exception:
                pass

def add_lead(lead: dict):
    with lock:
        # Calculate a mock signal strength score between 75.0 and 99.9 if not present
        if "score" not in lead:
            # Hash name to make it deterministic
            name_hash = sum(ord(c) for c in lead.get("name", "Unknown"))
            lead["score"] = round(75.0 + (name_hash % 250) / 10.0, 1)
        
        active_scan["leads"].append(lead)
        active_scan["entities_discovered"] = len(active_scan["leads"])
        
        # A contact is verified if there is a phone or email
        contacts = sum(1 for l in active_scan["leads"] if l.get("phone") or l.get("email"))
        active_scan["contacts_verified"] = contacts
        
        event_data = {
            "type": "lead",
            "data": lead,
            "stats": {
                "entities": active_scan["entities_discovered"],
                "contacts": active_scan["contacts_verified"],
                "state": active_scan["state"]
            }
        }
        for q in list(stream_queues):
            try:
                q.put_nowait(event_data)
            except Exception:
                pass

def run_scraper_task(req: SearchRequest):
    global active_scan
    
    with lock:
        active_scan["state"] = "ACTIVE"
        active_scan["task_id"] = str(uuid.uuid4())
        active_scan["niche"] = req.niche
        active_scan["city"] = req.city
        active_scan["country"] = req.country
        active_scan["entities_discovered"] = 0
        active_scan["contacts_verified"] = 0
        active_scan["logs"] = []
        active_scan["leads"] = []
    
    add_log(f"System initialized. Establishing connection to intelligence nodes...", True)
    add_log(f"Initiating search expansion for '{req.niche}' in '{req.city}, {req.country}'...")
    
    all_leads = []
    
    # 1. Google Maps
    if "google_maps" in req.sources:
        add_log("Starting Google Maps Scraper...")
        try:
            scraper = GoogleMapsScraper(headless=req.headless)
            
            def gm_callback(msg):
                add_log(msg)
                
            leads = scraper.scrape(
                req.niche, 
                req.city, 
                req.country, 
                req.max_results, 
                gm_callback, 
                broaden=req.broaden
            )
            for lead in leads:
                lead["source"] = "google_maps"
                add_lead(lead)
            all_leads.extend(leads)
            add_log(f"Google Maps: Found {len(leads)} raw leads.", True)
        except Exception as e:
            add_log(f"Google Maps Error: {str(e)}")
            logger.exception("Google Maps error")

    # 2. Yellow Pages
    if "yellowpages" in req.sources:
        add_log("Starting Yellow Pages / Yelp Scraper...")
        try:
            scraper = YellowPagesScraper()
            def yp_callback(msg):
                add_log(msg)
            leads = scraper.scrape(req.niche, req.city, req.country, req.max_results, yp_callback)
            for lead in leads:
                lead["source"] = "yellowpages"
                add_lead(lead)
            all_leads.extend(leads)
            add_log(f"Yellow Pages: Found {len(leads)} raw leads.", True)
        except Exception as e:
            add_log(f"Yellow Pages Error: {str(e)}")
            logger.exception("Yellow Pages error")

    # 3. Instagram
    if "instagram" in req.sources:
        add_log("Starting Instagram Scraper...")
        try:
            scraper = InstagramScraper()
            def insta_callback(msg):
                add_log(msg)
            leads = scraper.scrape(req.niche, req.city, req.country, req.max_results, insta_callback)
            for lead in leads:
                lead["source"] = "instagram"
                add_lead(lead)
            all_leads.extend(leads)
            add_log(f"Instagram Scraper completed. Found {len(leads)} raw leads.", True)
        except Exception as e:
            add_log(f"Instagram Error: {str(e)}")
            logger.exception("Instagram error")

    # 4. Facebook
    if "facebook" in req.sources:
        add_log("Starting Facebook Scraper...")
        try:
            # Extract urls from current leads to scrape FB pages
            urls_to_check = [l.get("website") for l in all_leads if l.get("website")]
            scraper = FacebookScraper(headless=req.headless)
            def fb_callback(msg):
                add_log(msg)
            leads = scraper.scrape(req.niche, req.city, req.country, req.max_results, fb_callback)
            for lead in leads:
                lead["source"] = "facebook"
                add_lead(lead)
            all_leads.extend(leads)
            add_log(f"Facebook Scraper completed. Found {len(leads)} raw leads.", True)
        except Exception as e:
            add_log(f"Facebook Error: {str(e)}")
            logger.exception("Facebook error")

    add_log("Post-processing: Deduplicating discovered leads...")
    deduped = deduplicate(all_leads)
    add_log(f"Deduplication complete: {len(deduped)} unique leads.", True)
    
    add_log("Filtering leads to identify businesses without websites...")
    no_website_leads = filter_no_website(deduped)
    add_log(f"Filtered results: {len(no_website_leads)} businesses found without a website.", True)
    
    # Save to local repository file
    os.makedirs("output", exist_ok=True)
    repo_file = "output/repository.json"
    existing_repo = []
    if os.path.exists(repo_file):
        try:
            with open(repo_file, "r") as f:
                existing_repo = json.load(f)
        except Exception:
            existing_repo = []
            
    # Add a date/timestamp to each lead
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for lead in no_website_leads:
        lead["timestamp"] = timestamp
        lead["status"] = "Active"
        
    existing_repo.extend(no_website_leads)
    
    # De-duplicate repository by name
    repo_dedup = []
    seen = set()
    for l in existing_repo:
        name_lower = l.get("name", "").lower().strip()
        if name_lower not in seen:
            seen.add(name_lower)
            repo_dedup.append(l)
            
    with open(repo_file, "w") as f:
        json.dump(repo_dedup, f, indent=2)
        
    # Export CSV and Excel files
    export_csv(no_website_leads, f"leads_{req.city}_{req.niche.replace(' ', '_')}.csv")
    export_excel(no_website_leads, f"leads_{req.city}_{req.niche.replace(' ', '_')}.xlsx")
    
    with lock:
        active_scan["state"] = "COMPLETED"
    
    add_log(f"Active scan completed successfully. Saved {len(no_website_leads)} to repository.", True)

@app.post("/api/search")
def start_search(req: SearchRequest, background_tasks: BackgroundTasks):
    global active_scan
    if active_scan["state"] == "ACTIVE":
        return {"status": "error", "message": "A scan is already in progress."}
    
    background_tasks.add_task(run_scraper_task, req)
    return {"status": "success", "message": "Search initiated."}

@app.get("/api/stream")
def stream_results():
    def event_generator():
        q = queue.Queue()
        with lock:
            stream_queues.append(q)
            
            # Send initial state and logs first
            initial_data = {
                "type": "init",
                "state": active_scan["state"],
                "niche": active_scan["niche"],
                "city": active_scan["city"],
                "country": active_scan["country"],
                "entities": active_scan["entities_discovered"],
                "contacts": active_scan["contacts_verified"],
                "logs": active_scan["logs"],
                "leads": active_scan["leads"],
                "latency": active_scan["latency"]
            }
            yield f"data: {json.dumps(initial_data)}\n\n"
            
        try:
            while True:
                item = q.get()
                yield f"data: {json.dumps(item)}\n\n"
        except GeneratorExit:
            with lock:
                stream_queues.remove(q)
                
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/repository")
def get_repository():
    repo_file = "output/repository.json"
    if not os.path.exists(repo_file):
        return []
    try:
        with open(repo_file, "r") as f:
            return json.load(f)
    except Exception:
        return []

@app.get("/api/state")
def get_state():
    return {
        "state": active_scan["state"],
        "niche": active_scan["niche"],
        "city": active_scan["city"],
        "country": active_scan["country"],
        "entities": active_scan["entities_discovered"],
        "contacts": active_scan["contacts_verified"],
        "latency": active_scan["latency"]
    }

@app.post("/api/repository/update-status")
def update_lead_status(data: Dict[str, Any]):
    repo_file = "output/repository.json"
    if not os.path.exists(repo_file):
        return {"status": "error", "message": "No repository file found."}
    try:
        with open(repo_file, "r") as f:
            leads = json.load(f)
            
        name = data.get("name")
        new_status = data.get("status")
        
        for l in leads:
            if l.get("name") == name:
                l["status"] = new_status
                break
                
        with open(repo_file, "w") as f:
            json.dump(leads, f, indent=2)
            
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.on_event("startup")
def seed_repository():
    os.makedirs("output", exist_ok=True)
    repo_file = "output/repository.json"
    if not os.path.exists(repo_file) or os.path.getsize(repo_file) < 5:
        with open(repo_file, "w") as f:
            json.dump([], f, indent=2)
        logger.info("Initialized empty repository database.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
