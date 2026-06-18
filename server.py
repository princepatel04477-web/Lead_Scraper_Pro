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
cancel_requested = False

class SearchStoppedException(Exception):
    pass

def check_cancel():
    global cancel_requested
    if cancel_requested:
        raise SearchStoppedException("Search stopped by user.")

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

def run_scraper_task(req: SearchRequest, task_id: str):
    global active_scan, cancel_requested
    
    cancel_requested = False
    with lock:
        active_scan["state"] = "ACTIVE"
        active_scan["task_id"] = task_id
        active_scan["niche"] = req.niche
        active_scan["city"] = req.city
        active_scan["country"] = req.country
        active_scan["entities_discovered"] = 0
        active_scan["contacts_verified"] = 0
        active_scan["logs"] = []
        active_scan["leads"] = []

    # Write initial history entry
    import datetime
    history_file = "output/search_history.json"
    os.makedirs("output", exist_ok=True)
    history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r") as f:
                history = json.load(f)
        except Exception:
            history = []
            
    history_entry = {
        "id": task_id,
        "niche": req.niche,
        "city": req.city,
        "country": req.country,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sources": req.sources,
        "entities_discovered": 0,
        "contacts_verified": 0,
        "status": "ACTIVE"
    }
    history.insert(0, history_entry)
    with open(history_file, "w") as f:
        json.dump(history, f, indent=2)
    
    add_log(f"System initialized. Establishing connection to intelligence nodes...", True)
    add_log(f"Initiating search expansion for '{req.niche}' in '{req.city}, {req.country}'...")
    
    all_leads = []
    try:
        # 1. Google Maps
        if "google_maps" in req.sources:
            check_cancel()
            add_log("Starting Google Maps Scraper...")
            try:
                scraper = GoogleMapsScraper(headless=req.headless)
                
                def gm_callback(msg):
                    check_cancel()
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
            except SearchStoppedException:
                raise
            except Exception as e:
                add_log(f"Google Maps Error: {str(e)}")
                logger.exception("Google Maps error")

        # 2. Yellow Pages
        if "yellowpages" in req.sources:
            check_cancel()
            add_log("Starting Yellow Pages / Yelp Scraper...")
            try:
                scraper = YellowPagesScraper()
                def yp_callback(msg):
                    check_cancel()
                    add_log(msg)
                leads = scraper.scrape(req.niche, req.city, req.country, req.max_results, yp_callback)
                for lead in leads:
                    lead["source"] = "yellowpages"
                    add_lead(lead)
                all_leads.extend(leads)
                add_log(f"Yellow Pages: Found {len(leads)} raw leads.", True)
            except SearchStoppedException:
                raise
            except Exception as e:
                add_log(f"Yellow Pages Error: {str(e)}")
                logger.exception("Yellow Pages error")

        # 3. Instagram
        if "instagram" in req.sources:
            check_cancel()
            add_log("Starting Instagram Scraper...")
            try:
                scraper = InstagramScraper()
                def insta_callback(msg):
                    check_cancel()
                    add_log(msg)
                leads = scraper.scrape(req.niche, req.city, req.country, req.max_results, insta_callback)
                for lead in leads:
                    lead["source"] = "instagram"
                    add_lead(lead)
                all_leads.extend(leads)
                add_log(f"Instagram Scraper completed. Found {len(leads)} raw leads.", True)
            except SearchStoppedException:
                raise
            except Exception as e:
                add_log(f"Instagram Error: {str(e)}")
                logger.exception("Instagram error")

        # 4. Facebook
        if "facebook" in req.sources:
            check_cancel()
            add_log("Starting Facebook Scraper...")
            try:
                scraper = FacebookScraper(headless=req.headless)
                def fb_callback(msg):
                    check_cancel()
                    add_log(msg)
                leads = scraper.scrape(req.niche, req.city, req.country, req.max_results, fb_callback)
                for lead in leads:
                    lead["source"] = "facebook"
                    add_lead(lead)
                all_leads.extend(leads)
                add_log(f"Facebook Scraper completed. Found {len(leads)} raw leads.", True)
            except SearchStoppedException:
                raise
            except Exception as e:
                add_log(f"Facebook Error: {str(e)}")
                logger.exception("Facebook error")

    except SearchStoppedException:
        add_log("Search execution stopped by user. Finalizing and saving gathered leads...", True)
    except Exception as e:
        logger.exception("Scraper execution encountered a fatal error during scanning")
        add_log(f"Scraper execution encountered a fatal error: {str(e)}")

    try:
        add_log("Post-processing: Deduplicating discovered leads...")
        deduped = deduplicate(all_leads)
        add_log(f"Deduplication complete: {len(deduped)} unique leads.", True)
        
        add_log("Filtering leads to identify businesses without websites...")
        no_website_leads = filter_no_website(deduped)
        add_log(f"Filtered results: {len(no_website_leads)} businesses found without a website.", True)
        
        # Save specific search results to leads_{task_id}.json
        leads_task_file = f"output/leads_{task_id}.json"
        timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for lead in no_website_leads:
            lead["timestamp"] = timestamp_str
            lead["status"] = "Active"
            
        with open(leads_task_file, "w") as f:
            json.dump(no_website_leads, f, indent=2)

        # Save to local repository file
        repo_file = "output/repository.json"
        existing_repo = []
        if os.path.exists(repo_file):
            try:
                with open(repo_file, "r") as f:
                    existing_repo = json.load(f)
            except Exception:
                existing_repo = []
                
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

        # Update history status to COMPLETED
        if os.path.exists(history_file):
            try:
                with open(history_file, "r") as f:
                    history = json.load(f)
                for h in history:
                    if h["id"] == task_id:
                        h["status"] = "COMPLETED"
                        h["entities_discovered"] = len(no_website_leads)
                        h["contacts_verified"] = sum(1 for l in no_website_leads if l.get("phone") or l.get("email"))
                        break
                with open(history_file, "w") as f:
                    json.dump(history, f, indent=2)
            except Exception:
                pass

    except Exception as e:
        logger.exception("Scraper execution error")
        with lock:
            active_scan["state"] = "ERROR"
        add_log(f"Scraper execution encountered a fatal error during post-processing: {str(e)}")
        # Update history status to ERROR
        if os.path.exists(history_file):
            try:
                with open(history_file, "r") as f:
                    history = json.load(f)
                for h in history:
                    if h["id"] == task_id:
                        h["status"] = "ERROR"
                        break
                with open(history_file, "w") as f:
                    json.dump(history, f, indent=2)
            except Exception:
                pass

@app.post("/api/search")
def start_search(req: SearchRequest, background_tasks: BackgroundTasks):
    global active_scan
    if active_scan["state"] == "ACTIVE":
        return {"status": "error", "message": "A scan is already in progress."}
    
    task_id = str(uuid.uuid4())
    background_tasks.add_task(run_scraper_task, req, task_id)
    return {"status": "success", "message": "Search initiated.", "task_id": task_id}

@app.post("/api/search/stop")
def stop_search():
    global cancel_requested, active_scan
    if active_scan["state"] != "ACTIVE":
        return {"status": "error", "message": "No active search to stop."}
    
    cancel_requested = True
    return {"status": "success", "message": "Stop signal sent to search tasks."}


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

@app.get("/api/history")
def get_search_history():
    history_file = "output/search_history.json"
    if not os.path.exists(history_file):
        return []
    try:
        with open(history_file, "r") as f:
            return json.load(f)
    except Exception:
        return []

@app.get("/api/history/{task_id}/leads")
def get_history_leads(task_id: str):
    leads_file = f"output/leads_{task_id}.json"
    if not os.path.exists(leads_file):
        return []
    try:
        with open(leads_file, "r") as f:
            return json.load(f)
    except Exception:
        return []

@app.on_event("startup")
def seed_repository():
    os.makedirs("output", exist_ok=True)
    repo_file = "output/repository.json"
    if not os.path.exists(repo_file) or os.path.getsize(repo_file) < 5:
        with open(repo_file, "w") as f:
            json.dump([], f, indent=2)
        logger.info("Initialized empty repository database.")

    # Seed Search History
    history_file = "output/search_history.json"
    if not os.path.exists(history_file) or os.path.getsize(history_file) < 5:
        history_seeds = [
            {
                "id": "mock-task-1",
                "niche": "Interior Design",
                "city": "London",
                "country": "United Kingdom",
                "timestamp": "2026-06-18 10:15:30",
                "sources": ["google_maps", "instagram"],
                "entities_discovered": 4,
                "contacts_verified": 4,
                "status": "COMPLETED"
            },
            {
                "id": "mock-task-2",
                "niche": "Roofing Contractors",
                "city": "Toronto",
                "country": "Canada",
                "timestamp": "2026-06-18 14:45:00",
                "sources": ["google_maps", "yellowpages"],
                "entities_discovered": 3,
                "contacts_verified": 2,
                "status": "COMPLETED"
            }
        ]
        with open(history_file, "w") as f:
            json.dump(history_seeds, f, indent=2)

        # Seed corresponding leads
        leads_1 = [
            { "name": "Aura Design Studio", "category": "Interior Design", "score": 92.4, "address": "London, UK", "phone": "+44 20 7946 0143", "email": "hello@auradesign.co.uk", "website": "auradesign.co.uk", "source": "google_maps" },
            { "name": "Bespoke Spaces Ltd", "category": "Interior Design", "score": 88.5, "address": "London, UK", "phone": "+44 20 7946 0188", "email": "info@bespokespaces.co.uk", "website": "bespokespaces.co.uk", "source": "instagram" },
            { "name": "Chelsea Interiors", "category": "Interior Design", "score": 86.1, "address": "London, UK", "phone": "+44 20 7946 0192", "email": "contact@chelseainteriors.com", "website": "chelseainteriors.com", "source": "google_maps" },
            { "name": "Design & Craft Co", "category": "Interior Design", "score": 81.3, "address": "London, UK", "phone": "+44 20 7946 0111", "email": "studios@designcraft.co.uk", "website": "designcraft.co.uk", "source": "instagram" }
        ]
        leads_2 = [
            { "name": "Apex Roofing Toronto", "category": "Roofing Contractors", "score": 96.2, "address": "Toronto, Canada", "phone": "+1 416-555-0182", "email": "quote@apexroofing.ca", "website": "apexroofing.ca", "source": "google_maps" },
            { "name": "Quality Shingles", "category": "Roofing Contractors", "score": 90.0, "address": "Toronto, Canada", "phone": "+1 416-555-0199", "email": "support@qualityshingles.ca", "website": "qualityshingles.ca", "source": "yellowpages" },
            { "name": "Metro Roofing Services", "category": "Roofing Contractors", "score": 84.5, "address": "Toronto, Canada", "phone": "+1 416-555-0122", "email": "", "website": "metroroofing.ca", "source": "google_maps" }
        ]

        with open("output/leads_mock-task-1.json", "w") as f:
            json.dump(leads_1, f, indent=2)
        with open("output/leads_mock-task-2.json", "w") as f:
            json.dump(leads_2, f, indent=2)
        logger.info("Seeded search history with mock past queries.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
