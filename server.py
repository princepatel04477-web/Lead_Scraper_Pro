import os
import sys
import uuid
import json
import time
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
from scrapers.intelligence_engine import LeadIntelligenceEngine
from utils.filters import filter_no_website, deduplicate
from utils.export import export_csv, export_excel
from utils.website_quality import WebsiteQualityIntelligenceSystem

intel_engine = LeadIntelligenceEngine()
website_quality_system = WebsiteQualityIntelligenceSystem()

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
lock = threading.RLock()

class SearchRequest(BaseModel):
    niche: str
    city: str
    country: str = ""
    sources: List[str] = ["google_maps", "yellowpages"]
    max_results: int = 50
    target_leads: int = 20
    worker_count: int = 6
    broaden: bool = True
    headless: bool = True

active_scan = {
    "task_id": None,
    "state": "IDLE", # IDLE, ACTIVE, COMPLETED, ERROR
    "niche": "",
    "city": "",
    "country": "",
    "companies_found": 0,
    "websites_verified": 0,
    "emails_extracted": 0,
    "phones_extracted": 0,
    "duplicates_removed": 0,
    "lead_quality_avg": 0.0,
    "active_workers": 0,
    "search_progress": 0.0,
    "entities_discovered": 0, # keep for backward compatibility
    "contacts_verified": 0,   # keep for backward compatibility
    "logs": [],
    "leads": [],
    "latency": 24,
    "workers_activity": {},
}

# Semaphore to limit max concurrent Selenium instances to protect RAM
selenium_semaphore = threading.Semaphore(3)

def add_log(msg: str, is_success: bool = False):
    with lock:
        log_entry = {"time": len(active_scan["logs"]), "message": msg, "is_success": is_success}
        active_scan["logs"].append(log_entry)
        
        # Dispatch to all connected SSE clients
        event_data = {
            "type": "log",
            "data": log_entry,
            "stats": {
                "state": active_scan["state"],
                "entities": active_scan["entities_discovered"],
                "contacts": active_scan["contacts_verified"],
                "companies_found": active_scan["companies_found"],
                "websites_verified": active_scan["websites_verified"],
                "emails_extracted": active_scan["emails_extracted"],
                "phones_extracted": active_scan["phones_extracted"],
                "duplicates_removed": active_scan["duplicates_removed"],
                "lead_quality_avg": active_scan["lead_quality_avg"],
                "active_workers": active_scan["active_workers"],
                "search_progress": active_scan["search_progress"],
                "workers_activity": active_scan.get("workers_activity", {})
            }
        }
        for q in list(stream_queues):
            try:
                q.put_nowait(event_data)
            except Exception:
                pass

def generate_query_buckets(niche: str, city: str, country: str, count: int) -> List[str]:
    from utils.geo_resolver import get_city_localities
    localities = get_city_localities(city)
    
    queries = []
    # All workers search the same niche. Only workload/geographic areas change.
    for loc in localities:
        queries.append(f"{niche} in {loc}, {city}")
        
    if len(queries) < count:
        queries.append(f"{niche} in {city} CBD")
        queries.append(f"{niche} in {city} Downtown")
        queries.append(f"{niche} near {city}")
        while len(queries) < count:
            queries.append(f"{niche} in {localities[len(queries) % len(localities)]}, {city}")
            
    return queries[:count]

def run_scraper_task(req: SearchRequest, task_id: str):
    global active_scan, cancel_requested
    
    cancel_requested = False
    target = req.target_leads if req.target_leads != 20 else (req.max_results if req.max_results != 50 else 20)
    
    # 1. Resolve Country if omitted
    if not req.country:
        from utils.geo_resolver import resolve_country
        req.country = resolve_country(req.city)
        add_log(f"Auto-resolved country from city '{req.city}' -> '{req.country}'", True)
        
    # 2. Respect User-Controlled Worker Count (min 1, max 12)
    W = max(1, min(12, req.worker_count))
    
    # 3. Generate Search buckets (Geographic expansion of business zones)
    query_buckets = generate_query_buckets(req.niche, req.city, req.country, W)

    # 3. Worker Status Helper
    def update_worker_status(worker_id):
        # Assumes caller holds lock
        if worker_id not in active_scan["workers_activity"]:
            return
        w = active_scan["workers_activity"][worker_id]
        if w.get("search_failed", False):
            w["status"] = "Error"
        elif w.get("extracting_count", 0) > 0:
            w["status"] = "Extracting Contacts"
        elif w.get("verifying_count", 0) > 0:
            w["status"] = "Verifying Websites"
        elif not w.get("search_done", False):
            w["status"] = "Searching"
        else:
            w["status"] = "Completed"
        
    with lock:
        active_scan["state"] = "ACTIVE"
        active_scan["task_id"] = task_id
        active_scan["niche"] = req.niche
        active_scan["city"] = req.city
        active_scan["country"] = req.country
        active_scan["companies_found"] = 0
        active_scan["websites_verified"] = 0
        active_scan["emails_extracted"] = 0
        active_scan["phones_extracted"] = 0
        active_scan["duplicates_removed"] = 0
        active_scan["no_website_leads"] = 0
        active_scan["poor_website_leads"] = 0
        active_scan["lead_quality_avg"] = 0.0
        active_scan["active_workers"] = 0
        active_scan["search_progress"] = 0.0
        active_scan["entities_discovered"] = 0
        active_scan["contacts_verified"] = 0
        active_scan["logs"] = []
        active_scan["leads"] = []
        active_scan["workers_activity"] = {
            f"Worker {i+1}": {
                "status": "Idle",
                "query": query_buckets[i],
                "leads_found": 0,
                "websites_verified": 0,
                "emails_extracted": 0,
                "phones_extracted": 0,
                "search_time": 0,
                "start_time": None,
                "search_done": False,
                "search_failed": False,
                "verifying_count": 0,
                "extracting_count": 0
            } for i in range(W)
        }

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
        
    add_log(f"System initialized with {W} parallel workers. Target leads: {target}.", True)
    add_log(f"Initiating search expansion for '{req.niche}' in '{req.city}, {req.country}'...")

    # Multi-Queue Setup
    company_queue = queue.Queue()       # Shared Company Queue
    verification_queue = queue.Queue()  # Shared Verification Queue
    contact_queue = queue.Queue()       # Shared Contact Queue
    
    stop_event = threading.Event()
    
    # Shared URL Queue lock registry
    shared_url_queue = {} # url -> {"status": "LOCKED", "assigned_worker": worker_id, "timestamp": time.time()}
    shared_url_lock = threading.Lock()
    
    # Global Deduplication structures
    visited_urls = set()
    visited_domains = set()
    visited_companies = set()
    visited_phones = set()
    dedup_lock = threading.Lock()
    
    import re
    import urllib.parse
    
    def is_duplicate_and_add(lead: dict) -> bool:
        name = lead.get("name", "")
        website = lead.get("website", "")
        phone = lead.get("phone", "")
        
        norm_name = re.sub(r"[^a-z0-9]", "", name.lower().strip())
        
        norm_domain = ""
        if website:
            parsed = urllib.parse.urlparse(website)
            domain = parsed.netloc or parsed.path
            norm_domain = domain.lower().replace("www.", "").strip()
            
        norm_phone = re.sub(r"[^0-9]", "", phone.strip())
        
        with dedup_lock:
            if norm_name and norm_name in visited_companies:
                return True
            if website and website in visited_urls:
                return True
            if norm_domain and norm_domain in visited_domains:
                return True
            if norm_phone and norm_phone in visited_phones:
                return True
                
            if norm_name:
                visited_companies.add(norm_name)
            if website:
                visited_urls.add(website)
            if norm_domain:
                visited_domains.add(norm_domain)
            if norm_phone:
                visited_phones.add(norm_phone)
                
            return False
            
    def claim_and_lock_url(url: str, worker_id: str) -> bool:
        if not url:
            return True
        with shared_url_lock:
            parsed = urllib.parse.urlparse(url)
            domain = (parsed.netloc or parsed.path).lower().replace("www.", "").strip()
            
            for locked_url, info in shared_url_queue.items():
                l_parsed = urllib.parse.urlparse(locked_url)
                l_domain = (l_parsed.netloc or l_parsed.path).lower().replace("www.", "").strip()
                if locked_url == url or l_domain == domain:
                    return False
                    
            shared_url_queue[url] = {
                "status": "LOCKED",
                "assigned_worker": worker_id,
                "timestamp": time.time()
            }
            return True
            
    def mark_url_completed(url: str):
        if not url:
            return
        with shared_url_lock:
            if url in shared_url_queue:
                shared_url_queue[url]["status"] = "COMPLETED"

    # Stage 1: Search Workers
    def search_worker_run(worker_idx, query):
        worker_name = f"Worker {worker_idx}"
        with lock:
            active_scan["active_workers"] += 1
            if worker_name in active_scan["workers_activity"]:
                active_scan["workers_activity"][worker_name]["status"] = "Searching"
                active_scan["workers_activity"][worker_name]["start_time"] = time.time()
                
        add_log(f"Worker {worker_idx} started searching bucket: '{query}'")
        
        def on_lead_discovered(lead):
            lead["worker_id"] = worker_name
            with lock:
                active_scan["companies_found"] += 1
                if worker_name in active_scan["workers_activity"]:
                    w = active_scan["workers_activity"][worker_name]
                    w["leads_found"] += 1
            company_queue.put(lead)

        try:
            for src in req.sources:
                if stop_event.is_set() or cancel_requested:
                    break
                
                if src == "google_maps":
                    add_log(f"Worker {worker_idx} requesting browser resource for maps...")
                    with selenium_semaphore:
                        if stop_event.is_set() or cancel_requested:
                            break
                        add_log(f"Worker {worker_idx} acquired browser. Scraping Google Maps...")
                        try:
                            scraper = GoogleMapsScraper(headless=req.headless)
                            scraper.scrape(
                                niche=query,
                                city=req.city,
                                country=req.country,
                                max_results=target,
                                progress_callback=None,
                                broaden=False,
                                lead_callback=on_lead_discovered,
                                stop_check=lambda: stop_event.is_set() or cancel_requested
                            )
                        except Exception as e:
                            logger.error(f"Worker {worker_idx} Google Maps Scraper failed: {e}")
                            
                elif src == "yellowpages":
                    try:
                        scraper = YellowPagesScraper()
                        scraper.scrape(
                            niche=query,
                            city=req.city,
                            country=req.country,
                            max_results=target,
                            progress_callback=None,
                            lead_callback=on_lead_discovered,
                            stop_check=lambda: stop_event.is_set() or cancel_requested
                        )
                    except Exception as e:
                        logger.error(f"Worker {worker_idx} YellowPages Scraper failed: {e}")
                        
                elif src == "instagram":
                    try:
                        scraper = InstagramScraper()
                        scraper.scrape(
                            niche=query,
                            city=req.city,
                            country=req.country,
                            max_results=target,
                            progress_callback=None,
                            lead_callback=on_lead_discovered,
                            stop_check=lambda: stop_event.is_set() or cancel_requested
                        )
                    except Exception as e:
                        logger.error(f"Worker {worker_idx} Instagram Scraper failed: {e}")
                        
                elif src == "facebook":
                    add_log(f"Worker {worker_idx} requesting browser resource for Facebook...")
                    with selenium_semaphore:
                        if stop_event.is_set() or cancel_requested:
                            break
                        add_log(f"Worker {worker_idx} acquired browser. Scraping Facebook...")
                        try:
                            scraper = FacebookScraper(headless=req.headless)
                            scraper.scrape(
                                niche=query,
                                city=req.city,
                                country=req.country,
                                max_results=target,
                                progress_callback=None,
                                lead_callback=on_lead_discovered,
                                stop_check=lambda: stop_event.is_set() or cancel_requested
                            )
                        except Exception as e:
                            logger.error(f"Worker {worker_idx} Facebook Scraper failed: {e}")
        except Exception as e:
            logger.error(f"Worker {worker_idx} encountered error: {e}")
            with lock:
                if worker_name in active_scan["workers_activity"]:
                    active_scan["workers_activity"][worker_name]["search_failed"] = True
        finally:
            with lock:
                active_scan["active_workers"] -= 1
                if worker_name in active_scan["workers_activity"]:
                    active_scan["workers_activity"][worker_name]["search_done"] = True
                    update_worker_status(worker_name)
            add_log(f"Worker {worker_idx} finished bucket: '{query}'")

    # Stage 2: Website Verification Workers
    def verification_worker_run(worker_idx):
        worker_id = f"Verification Worker {worker_idx}"
        while not stop_event.is_set() and not cancel_requested:
            try:
                lead = company_queue.get(timeout=0.5)
            except queue.Empty:
                continue
                
            if is_duplicate_and_add(lead):
                with lock:
                    active_scan["duplicates_removed"] += 1
                company_queue.task_done()
                continue
                
            website = lead.get("website", "")
            parent_worker_id = lead.get("worker_id")
            
            if website:
                if not claim_and_lock_url(website, worker_id):
                    # Already locked or processed by another worker
                    company_queue.task_done()
                    continue
            
            if parent_worker_id:
                with lock:
                    if parent_worker_id in active_scan["workers_activity"]:
                        active_scan["workers_activity"][parent_worker_id]["verifying_count"] += 1
                        update_worker_status(parent_worker_id)
            
            try:
                try:
                    res = website_quality_system.evaluate_website(website, lead)
                    lead.update(res)
                    if website:
                        mark_url_completed(website)
                except Exception as e:
                    logger.error(f"Error checking website {website}: {e}")
                    # default fallback
                    lead.update({
                        "website_exists": bool(website),
                        "website_opportunity_score": 100 if not website else 50,
                        "website_tier": "Tier E" if not website else "Tier C",
                        "website_health": "Broken" if website else "None",
                        "upgrade_opportunity": "High",
                        "website_checks": {}
                    })
                    if website:
                        mark_url_completed(website)
            finally:
                with lock:
                    active_scan["websites_verified"] += 1
                    if parent_worker_id and parent_worker_id in active_scan["workers_activity"]:
                        w = active_scan["workers_activity"][parent_worker_id]
                        w["websites_verified"] += 1
                        w["verifying_count"] = max(0, w["verifying_count"] - 1)
                        update_worker_status(parent_worker_id)
                
                verification_queue.put(lead)
                company_queue.task_done()

    # Stage 3: Contact Extraction Workers
    def contact_worker_run():
        while not stop_event.is_set() and not cancel_requested:
            try:
                lead = verification_queue.get(timeout=0.5)
            except queue.Empty:
                continue
                
            website = lead.get("website", "")
            parent_worker_id = lead.get("worker_id")
            
            if parent_worker_id:
                with lock:
                    if parent_worker_id in active_scan["workers_activity"]:
                        active_scan["workers_activity"][parent_worker_id]["extracting_count"] += 1
                        update_worker_status(parent_worker_id)
            
            try:
                if website:
                    try:
                        intel_engine.discover_keywords_from_url(lead["name"], website)
                    except Exception:
                        pass
            finally:
                with lock:
                    if parent_worker_id and parent_worker_id in active_scan["workers_activity"]:
                        w = active_scan["workers_activity"][parent_worker_id]
                        w["extracting_count"] = max(0, w["extracting_count"] - 1)
                        update_worker_status(parent_worker_id)
                
                contact_queue.put(lead)
                verification_queue.task_done()

    # Stage 4: Lead Scoring & DB Worker
    def scoring_worker_run():
        while not stop_event.is_set() and not cancel_requested:
            try:
                lead = contact_queue.get(timeout=0.5)
            except queue.Empty:
                continue
                
            score, breakdown = intel_engine.calculate_lead_score(lead)
            lead["score"] = float(score)
            lead["score_breakdown"] = breakdown
            
            # Populate Location details for advanced filtering
            lead["country"] = req.country
            lead["city"] = req.city
            lead["area"] = ""
            parent_worker_id = lead.get("worker_id")
            if parent_worker_id:
                with lock:
                    if parent_worker_id in active_scan["workers_activity"]:
                        q = active_scan["workers_activity"][parent_worker_id]["query"]
                        # Match 'in {locality}, {city}'
                        match = re.search(r"in\s+(.*?),\s*" + re.escape(req.city), q, re.I)
                        if match:
                            lead["area"] = match.group(1).strip().title()
                        else:
                            # fallback: clean query
                            area_clean = q.lower().replace(req.niche.lower(), "").replace(req.city.lower(), "").replace("in", "").replace(",", "").strip()
                            lead["area"] = area_clean.title()
            
            try:
                intel_engine.enrich_company_graph(lead)
            except Exception:
                pass
                
            with lock:
                if len(active_scan["leads"]) >= target:
                    contact_queue.task_done()
                    continue
                    
                active_scan["leads"].append(lead)
                active_scan["entities_discovered"] = len(active_scan["leads"])
                
                # Check tiers for metrics
                tier = lead.get("website_tier")
                if tier == "Tier E":
                    active_scan["no_website_leads"] = active_scan.get("no_website_leads", 0) + 1
                elif tier in ["Tier C", "Tier D"]:
                    active_scan["poor_website_leads"] = active_scan.get("poor_website_leads", 0) + 1
                
                # Update extraction stats
                emails = sum(1 for l in active_scan["leads"] if l.get("email"))
                phones = sum(1 for l in active_scan["leads"] if l.get("phone"))
                active_scan["emails_extracted"] = emails
                active_scan["phones_extracted"] = phones
                active_scan["contacts_verified"] = sum(1 for l in active_scan["leads"] if l.get("phone") or l.get("email"))
                
                # Update specific worker stats
                parent_worker_id = lead.get("worker_id")
                if parent_worker_id and parent_worker_id in active_scan["workers_activity"]:
                    w = active_scan["workers_activity"][parent_worker_id]
                    w["emails_extracted"] = sum(1 for l in active_scan["leads"] if l.get("worker_id") == parent_worker_id and l.get("email"))
                    w["phones_extracted"] = sum(1 for l in active_scan["leads"] if l.get("worker_id") == parent_worker_id and l.get("phone"))
                
                # Calculate average quality
                tot_score = sum(l.get("score", 0) for l in active_scan["leads"])
                active_scan["lead_quality_avg"] = round(tot_score / len(active_scan["leads"]), 1)
                
                # Search Progress
                active_scan["search_progress"] = round((len(active_scan["leads"]) / target) * 100, 1)
                
                # Stream Lead immediately
                event_data = {
                    "type": "lead",
                    "data": lead,
                    "stats": {
                        "state": active_scan["state"],
                        "entities": active_scan["entities_discovered"],
                        "contacts": active_scan["contacts_verified"],
                        "companies_found": active_scan["companies_found"],
                        "websites_verified": active_scan["websites_verified"],
                        "emails_extracted": active_scan["emails_extracted"],
                        "phones_extracted": active_scan["phones_extracted"],
                        "duplicates_removed": active_scan["duplicates_removed"],
                        "lead_quality_avg": active_scan["lead_quality_avg"],
                        "active_workers": active_scan["active_workers"],
                        "search_progress": active_scan["search_progress"],
                        "no_website_leads": active_scan.get("no_website_leads", 0),
                        "poor_website_leads": active_scan.get("poor_website_leads", 0),
                        "workers_activity": active_scan.get("workers_activity", {})
                    }
                }
                for q in list(stream_queues):
                    try:
                        q.put_nowait(event_data)
                    except Exception:
                        pass
                        
                # Terminate search if target is met
                if len(active_scan["leads"]) >= target:
                    stop_event.set()
                    add_log(f"Target count of {target} unique leads reached! Stopping all workers.", True)
                    
            contact_queue.task_done()

    # 4. Spawn threads
    search_threads = []
    for i in range(W):
        t = threading.Thread(target=search_worker_run, args=(i+1, query_buckets[i]), daemon=True)
        search_threads.append(t)
        t.start()
        
    verification_threads = []
    for i in range(4):
        t = threading.Thread(target=verification_worker_run, args=(i+1,), daemon=True)
        verification_threads.append(t)
        t.start()
        
    contact_threads = []
    for _ in range(4):
        t = threading.Thread(target=contact_worker_run, daemon=True)
        contact_threads.append(t)
        t.start()
        
    scoring_thread = threading.Thread(target=scoring_worker_run, daemon=True)
    scoring_thread.start()

    # 5. Monitor and Join
    try:
        # Wait for all search workers to finish (unless stop/cancel)
        while True:
            # Check cancel requested from API
            if cancel_requested:
                stop_event.set()
                add_log("Cancel signal received. Stopping search pipeline...")
                break
                
            # Update search time for active workers in active_scan
            with lock:
                now = time.time()
                for name, w in active_scan["workers_activity"].items():
                    if w["status"] in ["Searching", "Verifying Websites", "Extracting Contacts"] and w["start_time"] is not None:
                        w["search_time"] = int(now - w["start_time"])
                
                # Stream stats update
                event_data = {
                    "type": "stats",
                    "stats": {
                        "state": active_scan["state"],
                        "entities": active_scan["entities_discovered"],
                        "contacts": active_scan["contacts_verified"],
                        "companies_found": active_scan["companies_found"],
                        "websites_verified": active_scan["websites_verified"],
                        "emails_extracted": active_scan["emails_extracted"],
                        "phones_extracted": active_scan["phones_extracted"],
                        "duplicates_removed": active_scan["duplicates_removed"],
                        "lead_quality_avg": active_scan["lead_quality_avg"],
                        "active_workers": active_scan["active_workers"],
                        "search_progress": active_scan["search_progress"],
                        "no_website_leads": active_scan.get("no_website_leads", 0),
                        "poor_website_leads": active_scan.get("poor_website_leads", 0),
                        "workers_activity": active_scan.get("workers_activity", {})
                    }
                }
                for q in list(stream_queues):
                    try:
                        q.put_nowait(event_data)
                    except Exception:
                        pass
                
            # Check if all search threads are done
            if not any(t.is_alive() for t in search_threads):
                break
                
            time.sleep(0.5)
            
        # Join search threads
        for t in search_threads:
            t.join()
            
        # Drain queues
        while not stop_event.is_set() and not cancel_requested:
            if company_queue.empty() and verification_queue.empty() and contact_queue.empty():
                break
            time.sleep(0.5)
            
        # Stop remaining pipeline workers
        stop_event.set()
        
        # Join verification, contact and scoring threads
        for t in verification_threads:
            t.join(timeout=1.0)
        for t in contact_threads:
            t.join(timeout=1.0)
        scoring_thread.join(timeout=1.0)
        
    except Exception as e:
        logger.exception("Scraper pipeline watcher failed")
        add_log(f"Pipeline Watcher Error: {e}")
        
    # 6. Post-processing and saving results
    try:
        with lock:
            final_leads = list(active_scan["leads"])
            
        # Save specific search results to leads_{task_id}.json
        leads_task_file = f"output/leads_{task_id}.json"
        timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for lead in final_leads:
            lead["timestamp"] = timestamp_str
            lead["status"] = "Active"
            
        with open(leads_task_file, "w") as f:
            json.dump(final_leads, f, indent=2)

        # Save to local repository file
        repo_file = "output/repository.json"
        existing_repo = []
        if os.path.exists(repo_file):
            try:
                with open(repo_file, "r") as f:
                    existing_repo = json.load(f)
            except Exception:
                existing_repo = []
                
        existing_repo.extend(final_leads)
        
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
        export_csv(final_leads, f"leads_{req.city}_{req.niche.replace(' ', '_')}.csv")
        export_excel(final_leads, f"leads_{req.city}_{req.niche.replace(' ', '_')}.xlsx")
        
        # Recalculate stats for self-improving intelligence databases
        total_found = active_scan["companies_found"]
        unique_companies = len(final_leads)
        duplicate_results = active_scan["duplicates_removed"]
        emails_found = active_scan["emails_extracted"]
        phones_found = active_scan["phones_extracted"]
        avg_lead_score = active_scan["lead_quality_avg"]
        duplicate_rate = duplicate_results / max(total_found, 1)

        # 1. Update Keyword Performance (Module 1)
        try:
            intel_engine.record_search_performance(
                req.niche,
                unique_companies,
                emails_found,
                phones_found,
                duplicate_results,
                avg_lead_score
            )
            add_log("Self-Improving Engine: Updated Keyword Performance matrices.", True)
        except Exception as e:
            logger.error(f"Failed to record keyword performance: {e}")

        # 2. Update Source Performance (Module 4)
        try:
            for src in req.sources:
                intel_engine.record_source_performance(
                    src,
                    unique_companies // len(req.sources),
                    emails_found // len(req.sources),
                    phones_found // len(req.sources),
                    duplicate_results // len(req.sources),
                    avg_lead_score
                )
            add_log("Self-Improving Engine: Recalculated Source Efficiency metrics.", True)
        except Exception as e:
            logger.error(f"Failed to record source performance: {e}")

        # 3. Update Duplicate Learning & priority adjustment (Module 7)
        try:
            intel_engine.update_duplicate_learning(req.niche, req.city, duplicate_results, total_found)
            add_log("Self-Improving Engine: Adapted duplicate crawl rate restrictions.", True)
        except Exception as e:
            logger.error(f"Failed to update duplicate learning: {e}")

        # 4. Update Search Path Optimization (Module 6)
        try:
            intel_engine.record_search_path(
                f"{req.niche} in {req.city}",
                unique_companies,
                avg_lead_score,
                duplicate_rate
            )
            add_log("Self-Improving Engine: Analyzed search path success rates.", True)
        except Exception as e:
            logger.error(f"Failed to record search path optimization: {e}")

        # 5. Seed Industry Dictionary automatically if keyword performance is high (Module 5)
        try:
            intel_engine.add_industry_knowledge(req.niche, "keyword", req.niche)
            for l in final_leads[:3]:
                if l.get("category"):
                    intel_engine.add_industry_knowledge(req.niche, "synonym", l["category"])
                    intel_engine.add_competitor_expansion(req.niche, l["category"])
        except Exception as e:
            logger.error(f"Failed to seed industry dictionary: {e}")

        with lock:
            active_scan["state"] = "COMPLETED"
        
        add_log(f"Active scan completed successfully. Saved {len(final_leads)} unique leads to repository.", True)

        # Update history status to COMPLETED
        if os.path.exists(history_file):
            try:
                with open(history_file, "r") as f:
                    history = json.load(f)
                for h in history:
                    if h["id"] == task_id:
                        h["status"] = "COMPLETED"
                        h["entities_discovered"] = len(final_leads)
                        h["contacts_verified"] = sum(1 for l in final_leads if l.get("phone") or l.get("email"))
                        break
                with open(history_file, "w") as f:
                    json.dump(history, f, indent=2)
            except Exception:
                pass

    except Exception as e:
        logger.exception("Scraper pipeline post-processing failed")
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
                "latency": active_scan["latency"],
                "companies_found": active_scan["companies_found"],
                "websites_verified": active_scan["websites_verified"],
                "emails_extracted": active_scan["emails_extracted"],
                "phones_extracted": active_scan["phones_extracted"],
                "duplicates_removed": active_scan["duplicates_removed"],
                "lead_quality_avg": active_scan["lead_quality_avg"],
                "active_workers": active_scan["active_workers"],
                "search_progress": active_scan["search_progress"],
                "no_website_leads": active_scan.get("no_website_leads", 0),
                "poor_website_leads": active_scan.get("poor_website_leads", 0),
                "workers_activity": active_scan.get("workers_activity", {})
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
