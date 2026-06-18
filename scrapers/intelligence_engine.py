import os
import re
import json
import sqlite3
import logging
import datetime
import random
from typing import List, Dict, Any, Tuple

logger = logging.getLogger("intelligence")

STOP_WORDS = {
    'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 'your', 'yours', 'yourself', 'yourselves',
    'he', 'him', 'his', 'himself', 'she', 'her', 'hers', 'herself', 'it', 'its', 'itself', 'they', 'them', 'their',
    'theirs', 'themselves', 'what', 'which', 'who', 'whom', 'this', 'that', 'these', 'those', 'am', 'is', 'are',
    'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'a', 'an',
    'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with', 'about',
    'against', 'between', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up',
    'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when',
    'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no',
    'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don',
    'should', 'now', 'd', 'll', 'm', 'o', 're', 've', 'y', 'ain', 'aren', 'couldn', 'didn', 'doesn', 'hadn',
    'hasn', 'haven', 'isn', 'ma', 'mightn', 'mustn', 'needn', 'shan', 'shouldn', 'wasn', 'weren', 'won', 'wouldn',
    'company', 'firm', 'agency', 'studio', 'provider', 'consultant', 'enterprise', 'startup', 'organization',
    'us', 'we', 'about', 'contact', 'services', 'home', 'business', 'find', 'get', 'our'
}

class LeadIntelligenceEngine:
    def __init__(self, db_path: str = "output/intelligence.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()
        
        # Module 1: Keyword Performance Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS keyword_performance (
                keyword TEXT PRIMARY KEY,
                searches_run INTEGER DEFAULT 0,
                leads_found INTEGER DEFAULT 0,
                unique_companies INTEGER DEFAULT 0,
                emails_found INTEGER DEFAULT 0,
                phones_found INTEGER DEFAULT 0,
                duplicate_results INTEGER DEFAULT 0,
                average_lead_score REAL DEFAULT 0.0,
                performance_score REAL DEFAULT 0.0,
                last_used TEXT
            )
        """)

        # Module 2: Discovered Keywords Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS discovered_keywords (
                keyword TEXT PRIMARY KEY,
                frequency INTEGER DEFAULT 0,
                source_company TEXT,
                confidence_score REAL DEFAULT 0.0
            )
        """)

        # Module 3: Competitor Expansion Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS competitor_expansion (
                industry TEXT,
                related_industry TEXT,
                PRIMARY KEY (industry, related_industry)
            )
        """)

        # Module 4: Source Intelligence Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS source_intelligence (
                source TEXT PRIMARY KEY,
                searches INTEGER DEFAULT 0,
                leads_found INTEGER DEFAULT 0,
                emails_found INTEGER DEFAULT 0,
                phones_found INTEGER DEFAULT 0,
                duplicate_rate REAL DEFAULT 0.0,
                average_lead_score REAL DEFAULT 0.0,
                efficiency REAL DEFAULT 1.0
            )
        """)

        # Module 5: Industry Knowledge Base Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS industry_knowledge_base (
                industry TEXT,
                term_type TEXT, -- 'keyword', 'service', 'synonym', 'related_industry'
                term TEXT,
                PRIMARY KEY (industry, term_type, term)
            )
        """)

        # Module 6: Search Path Optimization Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_path_optimization (
                path_query TEXT PRIMARY KEY,
                leads_found INTEGER DEFAULT 0,
                quality_score REAL DEFAULT 0.0,
                duplicate_rate REAL DEFAULT 0.0,
                success_rate REAL DEFAULT 0.0,
                rank_score REAL DEFAULT 0.0
            )
        """)

        # Module 7: Duplicate Learning Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS duplicate_learning (
                niche TEXT,
                city TEXT,
                duplicate_rate REAL DEFAULT 0.0,
                priority REAL DEFAULT 1.0,
                crawl_depth INTEGER DEFAULT 50,
                PRIMARY KEY (niche, city)
            )
        """)

        # Module 9: Company Knowledge Graph Tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS graph_nodes (
                id TEXT PRIMARY KEY,
                type TEXT, -- 'company', 'service', 'keyword', 'industry', 'location', 'source'
                label TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS graph_edges (
                source_id TEXT,
                target_id TEXT,
                type TEXT, -- 'OFFERS', 'MENTIONS', 'LOCATED_IN', 'FOUND_BY', 'COMPETES_WITH'
                PRIMARY KEY (source_id, target_id, type),
                FOREIGN KEY (source_id) REFERENCES graph_nodes(id),
                FOREIGN KEY (target_id) REFERENCES graph_nodes(id)
            )
        """)
        
        self.conn.commit()

    # Module 1: Keyword Intelligence
    def record_search_performance(self, keyword: str, unique_companies: int, emails_found: int, phones_found: int, duplicate_results: int, avg_lead_score: float):
        cursor = self.conn.cursor()
        
        # Calculate performance score
        # Formula: (unique_companies * 2) + (emails_found * 3) + (phones_found * 2) + average_lead_score - (duplicate_results * 2)
        performance_score = (unique_companies * 2) + (emails_found * 3) + (phones_found * 2) + avg_lead_score - (duplicate_results * 2)
        
        cursor.execute("""
            SELECT * FROM keyword_performance WHERE keyword = ?
        """, (keyword,))
        row = cursor.fetchone()
        
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if row:
            # Running average updates
            new_searches = row["searches_run"] + 1
            new_leads = row["leads_found"] + unique_companies + duplicate_results
            new_uniques = row["unique_companies"] + unique_companies
            new_emails = row["emails_found"] + emails_found
            new_phones = row["phones_found"] + phones_found
            new_duplicates = row["duplicate_results"] + duplicate_results
            
            # Cumulative average lead score
            new_avg_score = ((row["average_lead_score"] * row["searches_run"]) + avg_lead_score) / new_searches
            
            # Performance score recalculation
            new_perf_score = (new_uniques * 2) + (new_emails * 3) + (new_phones * 2) + new_avg_score - (new_duplicates * 2)
            
            cursor.execute("""
                UPDATE keyword_performance
                SET searches_run = ?, leads_found = ?, unique_companies = ?, emails_found = ?, phones_found = ?, duplicate_results = ?, average_lead_score = ?, performance_score = ?, last_used = ?
                WHERE keyword = ?
            """, (new_searches, new_leads, new_uniques, new_emails, new_phones, new_duplicates, new_avg_score, new_perf_score, now_str, keyword))
        else:
            cursor.execute("""
                INSERT INTO keyword_performance (keyword, searches_run, leads_found, unique_companies, emails_found, phones_found, duplicate_results, average_lead_score, performance_score, last_used)
                VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (keyword, unique_companies + duplicate_results, unique_companies, emails_found, phones_found, duplicate_results, avg_lead_score, performance_score, now_str))
            
        self.conn.commit()

    # Module 2: Automatic Keyword Discovery (TF-IDF & Frequency Extraction)
    def discover_keywords_from_content(self, company_name: str, content_blocks: Dict[str, str]):
        """
        Normalize content_blocks, remove stop words, compute frequencies, and store in discovered_keywords.
        """
        word_freq = {}
        for block_name, text in content_blocks.items():
            if not text:
                continue
            # Normalize: lowercase, remove non-alphanumeric (except space/hyphen)
            clean_text = re.sub(r'[^a-zA-Z0-9\s-]', '', text.lower())
            words = clean_text.split()
            
            # Process single words
            for w in words:
                w = w.strip()
                if len(w) > 3 and w not in STOP_WORDS:
                    word_freq[w] = word_freq.get(w, 0) + 1
                    
            # Process bigrams (2-word phrases)
            for i in range(len(words) - 1):
                w1, w2 = words[i], words[i+1]
                if w1 not in STOP_WORDS and w2 not in STOP_WORDS:
                    phrase = f"{w1} {w2}"
                    word_freq[phrase] = word_freq.get(phrase, 0) + 2

        cursor = self.conn.cursor()
        for phrase, freq in word_freq.items():
            # Calculate confidence score (frequency weight based on phrase length)
            phrase_words = phrase.split()
            word_count_multiplier = 1.5 if len(phrase_words) > 1 else 1.0
            confidence_score = freq * word_count_multiplier
            
            cursor.execute("""
                SELECT * FROM discovered_keywords WHERE keyword = ?
            """, (phrase,))
            row = cursor.fetchone()
            
            if row:
                cursor.execute("""
                    UPDATE discovered_keywords
                    SET frequency = frequency + ?, confidence_score = confidence_score + ?
                    WHERE keyword = ?
                """, (freq, confidence_score, phrase))
            else:
                cursor.execute("""
                    INSERT INTO discovered_keywords (keyword, frequency, source_company, confidence_score)
                    VALUES (?, ?, ?, ?)
                """, (phrase, freq, company_name, confidence_score))
                
        self.conn.commit()

    def discover_keywords_from_url(self, company_name: str, url: str):
        if not url:
            return
        if not url.startswith('http'):
            url = 'http://' + url
        try:
            import requests
            from bs4 import BeautifulSoup
            r = requests.get(url, timeout=4, headers={'User-Agent': 'Mozilla/5.0'})
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                page_title = soup.title.string if soup.title else ""
                h1_tags = " ".join([h.get_text() for h in soup.find_all('h1')])
                
                meta_desc = ""
                meta_d = soup.find('meta', attrs={'name': 'description'})
                if meta_d:
                    meta_desc = meta_d.get('content', '')
                    
                meta_kws = ""
                meta_k = soup.find('meta', attrs={'name': 'keywords'})
                if meta_k:
                    meta_kws = meta_k.get('content', '')
                
                content_blocks = {
                    "page_title": page_title,
                    "h1_tags": h1_tags,
                    "meta_description": meta_desc,
                    "meta_keywords": meta_kws
                }
                self.discover_keywords_from_content(company_name, content_blocks)
        except Exception as e:
            logger.debug(f"Failed to crawl website {url} for keyword discovery: {e}")

    # Module 3: Competitor Niche Expansion Engine
    def add_competitor_expansion(self, industry: str, related_industry: str):
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO competitor_expansion (industry, related_industry)
                VALUES (?, ?)
            """, (industry.strip().lower(), related_industry.strip().lower()))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error saving competitor expansion: {e}")

    # Module 4: Source Efficiency Intelligence
    def record_source_performance(self, source: str, leads_found: int, emails_found: int, phones_found: int, duplicate_count: int, avg_lead_score: float):
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT * FROM source_intelligence WHERE source = ?", (source,))
        row = cursor.fetchone()
        
        total_discovered = leads_found + duplicate_count
        duplicate_rate = duplicate_count / max(total_discovered, 1)
        
        if row:
            new_searches = row["searches"] + 1
            new_leads = row["leads_found"] + leads_found
            new_emails = row["emails_found"] + emails_found
            new_phones = row["phones_found"] + phones_found
            new_dup_rate = ((row["duplicate_rate"] * row["searches"]) + duplicate_rate) / new_searches
            new_avg_score = ((row["average_lead_score"] * row["searches"]) + avg_lead_score) / new_searches
            
            # Efficiency calculation formula:
            # (leads_found * 1.5 + emails_found * 2 + phones_found * 1.5) * (1 - duplicate_rate) * average_lead_score / 100
            new_efficiency = (new_leads * 1.5 + new_emails * 2.0 + new_phones * 1.5) * (1.0 - new_dup_rate) * (new_avg_score / 100.0)
            
            cursor.execute("""
                UPDATE source_intelligence
                SET searches = ?, leads_found = ?, emails_found = ?, phones_found = ?, duplicate_rate = ?, average_lead_score = ?, efficiency = ?
                WHERE source = ?
            """, (new_searches, new_leads, new_emails, new_phones, new_dup_rate, new_avg_score, max(new_efficiency, 0.1), source))
        else:
            efficiency = (leads_found * 1.5 + emails_found * 2.0 + phones_found * 1.5) * (1.0 - duplicate_rate) * (avg_lead_score / 100.0)
            cursor.execute("""
                INSERT INTO source_intelligence (source, searches, leads_found, emails_found, phones_found, duplicate_rate, average_lead_score, efficiency)
                VALUES (?, 1, ?, ?, ?, ?, ?, ?)
            """, (source, leads_found, emails_found, phones_found, duplicate_rate, avg_lead_score, max(efficiency, 0.1)))
            
        self.conn.commit()

    def get_source_allocations(self, default_sources: List[str]) -> Dict[str, float]:
        """
        Determine how to distribute search limit / crawl efforts to sources based on calculated efficiency weights.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT source, efficiency FROM source_intelligence")
        rows = cursor.fetchall()
        
        efficiencies = {row["source"]: row["efficiency"] for row in rows}
        
        # Merge with defaults
        weights = {}
        total = 0.0
        for src in default_sources:
            eff = efficiencies.get(src, 1.0) # default efficiency weight
            weights[src] = eff
            total += eff
            
        # Normalize weights so they sum to 1.0
        if total > 0:
            return {src: eff / total for src, eff in weights.items()}
        return {src: 1.0 / len(default_sources) for src in default_sources}

    # Module 5: Industry Knowledge Base dictionary
    def add_industry_knowledge(self, industry: str, term_type: str, term: str):
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO industry_knowledge_base (industry, term_type, term)
                VALUES (?, ?, ?)
            """, (industry.strip().lower(), term_type.strip(), term.strip().lower()))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error saving industry knowledge: {e}")

    def get_industry_dictionary(self, industry: str) -> Dict[str, List[str]]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT term_type, term FROM industry_knowledge_base WHERE industry = ?
        """, (industry.lower(),))
        rows = cursor.fetchall()
        
        result = {'keyword': [], 'service': [], 'synonym': [], 'related_industry': []}
        for row in rows:
            tt = row["term_type"]
            if tt in result:
                result[tt].append(row["term"])
        return result

    # Module 6: Search Path Optimization
    def record_search_path(self, path_query: str, leads_found: int, quality_score: float, duplicate_rate: float):
        cursor = self.conn.cursor()
        
        success_rate = 1.0 if leads_found > 0 else 0.0
        # Rank score formula
        rank_score = (leads_found * 1.5 + quality_score * 2.0) * (1.0 - duplicate_rate)
        
        cursor.execute("SELECT * FROM search_path_optimization WHERE path_query = ?", (path_query,))
        row = cursor.fetchone()
        
        if row:
            new_leads = row["leads_found"] + leads_found
            new_quality = (row["quality_score"] + quality_score) / 2.0
            new_dup = (row["duplicate_rate"] + duplicate_rate) / 2.0
            new_success = (row["success_rate"] + success_rate) / 2.0
            new_rank = (new_leads * 1.5 + new_quality * 2.0) * (1.0 - new_dup)
            
            cursor.execute("""
                UPDATE search_path_optimization
                SET leads_found = ?, quality_score = ?, duplicate_rate = ?, success_rate = ?, rank_score = ?
                WHERE path_query = ?
            """, (new_leads, new_quality, new_dup, new_success, new_rank, path_query))
        else:
            cursor.execute("""
                INSERT INTO search_path_optimization (path_query, leads_found, quality_score, duplicate_rate, success_rate, rank_score)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (path_query, leads_found, quality_score, duplicate_rate, success_rate, rank_score))
            
        self.conn.commit()

    # Module 7: Duplicate Learning & Adaptive Crawl Depth
    def update_duplicate_learning(self, niche: str, city: str, duplicate_companies: int, total_companies_found: int):
        cursor = self.conn.cursor()
        
        duplicate_rate = duplicate_companies / max(total_companies_found, 1)
        
        cursor.execute("SELECT * FROM duplicate_learning WHERE niche = ? AND city = ?", (niche.lower(), city.lower()))
        row = cursor.fetchone()
        
        # Adjust priorities & depth based on duplicate rate
        # If duplicate rate is high (>40%), reduce priority and depth to avoid exhausting requests
        if duplicate_rate > 0.4:
            priority = 0.5
            crawl_depth = 20
        elif duplicate_rate < 0.1:
            priority = 1.5
            crawl_depth = 100
        else:
            priority = 1.0
            crawl_depth = 50
            
        if row:
            new_dup_rate = (row["duplicate_rate"] + duplicate_rate) / 2.0
            new_priority = max(0.1, min(row["priority"] * (1.0 - duplicate_rate * 0.5), 2.0))
            new_depth = int(row["crawl_depth"] * (1.0 - duplicate_rate * 0.3))
            
            cursor.execute("""
                UPDATE duplicate_learning
                SET duplicate_rate = ?, priority = ?, crawl_depth = ?
                WHERE niche = ? AND city = ?
            """, (new_dup_rate, new_priority, max(new_depth, 10), niche.lower(), city.lower()))
        else:
            cursor.execute("""
                INSERT INTO duplicate_learning (niche, city, duplicate_rate, priority, crawl_depth)
                VALUES (?, ?, ?, ?, ?)
            """, (niche.lower(), city.lower(), duplicate_rate, priority, crawl_depth))
            
        self.conn.commit()

    def get_crawl_settings(self, niche: str, city: str) -> Tuple[float, int]:
        """
        Returns priority and max results crawl limit for a specific search space.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT priority, crawl_depth FROM duplicate_learning WHERE niche = ? AND city = ?", (niche.lower(), city.lower()))
        row = cursor.fetchone()
        if row:
            return row["priority"], row["crawl_depth"]
        return 1.0, 50

    # Module 8: Lead Quality Engine
    def calculate_lead_score(self, lead: dict) -> Tuple[int, Dict[str, int]]:
        """
        Lead Score Range: 0–100. Deterministic rules.
        - Website Exists = +10
        - Email Found = +20
        - Phone Found = +15
        - LinkedIn Found = +10
        - Recent Activity / Timestamp exists = +15
        - Multiple Contacts = +20
        - Company Size or Rating Identified = +10
        """
        score = 0
        breakdown = {}
        
        # Website check
        if lead.get("website"):
            score += 10
            breakdown["website_exists"] = 10
            
        # Email check
        if lead.get("email"):
            score += 20
            breakdown["email_found"] = 20
            
        # Phone check
        if lead.get("phone"):
            score += 15
            breakdown["phone_found"] = 15
            
        # Social check
        if "linkedin" in lead.get("website", "").lower() or "linkedin" in lead.get("source", "").lower():
            score += 10
            breakdown["linkedin_found"] = 10
            
        # Recent activity / metadata existence
        if lead.get("timestamp") or lead.get("last_scraped"):
            score += 15
            breakdown["recent_activity"] = 15
            
        # Multiple contacts
        contact_points = 0
        if lead.get("email"): contact_points += 1
        if lead.get("phone"): contact_points += 1
        if lead.get("facebook_link") or lead.get("instagram_link"): contact_points += 1
        
        if contact_points > 1:
            score += 20
            breakdown["multiple_contacts"] = 20
            
        # Metadata richness (Score/Rating identified)
        if lead.get("score") or lead.get("rating"):
            score += 10
            breakdown["metadata_richness"] = 10
            
        final_score = min(max(score, 0), 100)
        return final_score, breakdown

    # Module 9: Company Knowledge Graph
    def enrich_company_graph(self, lead: dict):
        cursor = self.conn.cursor()
        
        company_id = f"company:{lead.get('name', 'unknown').lower().replace(' ', '_')}"
        company_label = lead.get('name', 'Unknown')
        
        # Insert company node
        cursor.execute("INSERT OR REPLACE INTO graph_nodes (id, type, label) VALUES (?, ?, ?)", (company_id, 'company', company_label))
        
        # Insert location relationship
        if lead.get("address"):
            loc = lead.get("address")
            loc_id = f"loc:{loc.lower().replace(' ', '_')}"
            cursor.execute("INSERT OR REPLACE INTO graph_nodes (id, type, label) VALUES (?, ?, ?)", (loc_id, 'location', loc))
            cursor.execute("INSERT OR REPLACE INTO graph_edges (source_id, target_id, type) VALUES (?, ?, ?)", (company_id, loc_id, 'LOCATED_IN'))
            
        # Insert category / industry relationship
        if lead.get("category"):
            ind = lead.get("category")
            ind_id = f"ind:{ind.lower().replace(' ', '_')}"
            cursor.execute("INSERT OR REPLACE INTO graph_nodes (id, type, label) VALUES (?, ?, ?)", (ind_id, 'industry', ind))
            cursor.execute("INSERT OR REPLACE INTO graph_edges (source_id, target_id, type) VALUES (?, ?, ?)", (company_id, ind_id, 'BELONGS_TO'))
            
        # Insert source relationships
        if lead.get("source"):
            src = lead.get("source")
            src_id = f"src:{src}"
            cursor.execute("INSERT OR REPLACE INTO graph_nodes (id, type, label) VALUES (?, ?, ?)", (src_id, 'source', src))
            cursor.execute("INSERT OR REPLACE INTO graph_edges (source_id, target_id, type) VALUES (?, ?, ?)", (company_id, src_id, 'FOUND_BY'))
            
        # Insert website details as keywords
        if lead.get("website"):
            web = lead.get("website")
            # Create a keyword based on url words
            words = re.findall(r'\w+', web)
            for w in words:
                if len(w) > 3 and w not in STOP_WORDS and not w.isdigit():
                    kw_id = f"kw:{w.lower()}"
                    cursor.execute("INSERT OR REPLACE INTO graph_nodes (id, type, label) VALUES (?, ?, ?)", (kw_id, 'keyword', w))
                    cursor.execute("INSERT OR REPLACE INTO graph_edges (source_id, target_id, type) VALUES (?, ?, ?)", (company_id, kw_id, 'MENTIONS'))

        self.conn.commit()

    def get_graph_neighbors(self, node_id: str, max_depth: int = 2) -> List[Tuple[str, str, str]]:
        """
        Traverses relationships deterministically to suggest adjacent search targets.
        """
        cursor = self.conn.cursor()
        
        # Run a simple self-join query to find 1st and 2nd degree nodes
        cursor.execute("""
            SELECT n.id, n.type, n.label 
            FROM graph_nodes n
            JOIN graph_edges e ON n.id = e.target_id
            WHERE e.source_id = ?
        """, (node_id,))
        first_degree = cursor.fetchall()
        
        neighbors = []
        for row in first_degree:
            neighbors.append((row["id"], row["type"], row["label"]))
            
        return neighbors

    # Module 10: Adaptive Search Allocation (Multi-Armed Bandit strategy)
    def get_adaptive_keywords(self, niche: str, count: int = 10) -> List[str]:
        """
        Explore vs Exploit keyword prioritization.
        Allocates:
        - 70% top-performing keywords (performance_score > avg)
        - 20% medium-performing keywords
        - 10% experimental keywords (newly discovered candidates)
        """
        cursor = self.conn.cursor()
        
        # Fetch classified keywords
        cursor.execute("""
            SELECT keyword, performance_score 
            FROM keyword_performance 
            ORDER BY performance_score DESC
        """)
        perf_rows = cursor.fetchall()
        
        cursor.execute("""
            SELECT keyword, confidence_score 
            FROM discovered_keywords 
            ORDER BY confidence_score DESC
        """)
        disc_rows = cursor.fetchall()
        
        top_kws = [r["keyword"] for r in perf_rows]
        exp_kws = [r["keyword"] for r in disc_rows]
        
        # Add basic fallback keywords
        default_kws = [
            niche,
            f"{niche} office",
            f"best {niche}",
            f"local {niche}",
            f"{niche} services",
            f"{niche} consultant",
            f"{niche} agency",
            f"{niche} solutions"
        ]
        
        selected = []
        
        # Bandit Allocation counts
        top_count = int(count * 0.7)
        med_count = int(count * 0.2)
        exp_count = count - top_count - med_count
        
        # 1. Top performers
        selected.extend(top_kws[:top_count])
        
        # 2. Medium performers
        if len(top_kws) > top_count:
            med_pool = top_kws[top_count:]
            random.shuffle(med_pool)
            selected.extend(med_pool[:med_count])
            
        # 3. Experimental
        selected.extend(exp_kws[:exp_count])
        
        # Fill remaining with defaults if pools are small
        for kw in default_kws:
            if len(selected) >= count:
                break
            if kw not in selected:
                selected.append(kw)
                
        return selected[:count]
