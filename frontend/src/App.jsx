import React, { useState, useEffect, useRef } from 'react';
import SearchWorkspace from './components/SearchWorkspace';
import LiveIntelligence from './components/LiveIntelligence';
import ResultsStream from './components/ResultsStream';
import LeadRepository from './components/LeadRepository';

const DEFAULT_API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('Search');
  const [isScanning, setIsScanning] = useState(false);
  const [currentAction, setCurrentAction] = useState('');
  const [apiBaseUrl, setApiBaseUrl] = useState(DEFAULT_API_BASE);
  
  // Real-time scan state
  const [logs, setLogs] = useState([]);
  const [streamedLeads, setStreamedLeads] = useState([]);
  const [stats, setStats] = useState({
    state: 'IDLE',
    niche: '',
    city: '',
    country: '',
    entities: 0,
    contacts: 0
  });

  // Saved leads repository state
  const [repository, setRepository] = useState([]);
  
  // Search history state
  const [searchHistory, setSearchHistory] = useState([]);
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [showHelpModal, setShowHelpModal] = useState(false);
  
  const [settings, setSettings] = useState({
    defaultMaxResults: 50,
    mockModeForce: false
  });
  
  const eventSourceRef = useRef(null);
  const mockIntervalRef = useRef(null);

  // Fetch repository leads
  const fetchRepository = async () => {
    try {
      const resp = await fetch(`${apiBaseUrl}/repository`);
      if (resp.ok) {
        const data = await resp.json();
        setRepository(data);
      }
    } catch (err) {
      console.warn('Backend offline. Using local storage or empty repository.');
      const localRepo = localStorage.getItem('lead_repository');
      if (localRepo) {
        setRepository(JSON.parse(localRepo));
      } else {
        setRepository([]);
      }
    }
  };

  // Fetch search history
  const fetchSearchHistory = async () => {
    try {
      const resp = await fetch(`${apiBaseUrl}/history`);
      if (resp.ok) {
        const data = await resp.json();
        setSearchHistory(data);
      }
    } catch (err) {
      console.warn('Backend offline. Loading search history from localStorage.');
      const localHistory = localStorage.getItem('search_history');
      if (localHistory) {
        setSearchHistory(JSON.parse(localHistory));
      } else {
        // Seed some initial local mock searches if empty
        const initialMockHistory = [
          {
            id: "mock-task-1",
            niche: "Interior Design",
            city: "London",
            country: "United Kingdom",
            timestamp: "2026-06-18 10:15:30",
            sources: ["google_maps", "instagram"],
            entities_discovered: 4,
            contacts_verified: 4,
            status: "COMPLETED"
          },
          {
            id: "mock-task-2",
            niche: "Roofing Contractors",
            city: "Toronto",
            country: "Canada",
            timestamp: "2026-06-18 14:45:00",
            sources: ["google_maps", "yellowpages"],
            entities_discovered: 3,
            contacts_verified: 2,
            status: "COMPLETED"
          }
        ];
        setSearchHistory(initialMockHistory);
        localStorage.setItem('search_history', JSON.stringify(initialMockHistory));

        // Seed corresponding leads in localStorage
        const leads_1 = [
          { name: "Aura Design Studio", category: "Interior Design", score: 92.4, address: "London, UK", phone: "+44 20 7946 0143", email: "hello@auradesign.co.uk", website: "auradesign.co.uk", source: "google_maps" },
          { name: "Bespoke Spaces Ltd", category: "Interior Design", score: 88.5, address: "London, UK", phone: "+44 20 7946 0188", email: "info@bespokespaces.co.uk", website: "bespokespaces.co.uk", source: "instagram" },
          { name: "Chelsea Interiors", category: "Interior Design", score: 86.1, address: "London, UK", phone: "+44 20 7946 0192", email: "contact@chelseainteriors.com", website: "chelseainteriors.com", source: "google_maps" },
          { name: "Design & Craft Co", category: "Interior Design", score: 81.3, address: "London, UK", phone: "+44 20 7946 0111", email: "studios@designcraft.co.uk", website: "designcraft.co.uk", source: "instagram" }
        ];
        const leads_2 = [
          { name: "Apex Roofing Toronto", category: "Roofing Contractors", score: 96.2, address: "Toronto, Canada", phone: "+1 416-555-0182", email: "quote@apexroofing.ca", website: "apexroofing.ca", source: "google_maps" },
          { name: "Quality Shingles", category: "Roofing Contractors", score: 90.0, address: "Toronto, Canada", phone: "+1 416-555-0199", email: "support@qualityshingles.ca", website: "qualityshingles.ca", source: "yellowpages" },
          { name: "Metro Roofing Services", category: "Roofing Contractors", score: 84.5, address: "Toronto, Canada", phone: "+1 416-555-0122", email: "", website: "metroroofing.ca", source: "google_maps" }
        ];
        localStorage.setItem("leads_mock-task-1", JSON.stringify(leads_1));
        localStorage.setItem("leads_mock-task-2", JSON.stringify(leads_2));
      }
    }
  };

  // Sync state with backend on startup
  useEffect(() => {
    fetchRepository();
    fetchSearchHistory();

    const checkState = async () => {
      try {
        const resp = await fetch(`${apiBaseUrl}/state`);
        if (resp.ok) {
          const stateData = await resp.json();
          if (stateData.state === 'ACTIVE') {
            setIsScanning(true);
            setStats(stateData);
            setupEventSource();
            setActiveTab('Intelligence');
          }
        }
      } catch (err) {
        console.log('Backend server not detected.');
      }
    };
    checkState();

    return () => {
      if (eventSourceRef.current) eventSourceRef.current.close();
      if (mockIntervalRef.current) clearInterval(mockIntervalRef.current);
    };
  }, [apiBaseUrl]);

  // Connect to SSE stream
  const setupEventSource = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const source = new EventSource(`${apiBaseUrl}/stream`);
    eventSourceRef.current = source;

    source.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'init') {
        setLogs(data.logs || []);
        setStreamedLeads(data.leads || []);
        setStats({
          state: data.state,
          niche: data.niche,
          city: data.city,
          country: data.country,
          entities: data.entities,
          contacts: data.contacts,
          companies_found: data.companies_found || 0,
          websites_verified: data.websites_verified || 0,
          emails_extracted: data.emails_extracted || 0,
          phones_extracted: data.phones_extracted || 0,
          duplicates_removed: data.duplicates_removed || 0,
          lead_quality_avg: data.lead_quality_avg || 0.0,
          active_workers: data.active_workers || 0,
          search_progress: data.search_progress || 0.0,
          workers_activity: data.workers_activity || {}
        });
        setIsScanning(data.state === 'ACTIVE');
      } else if (data.type === 'log') {
        setLogs(prev => [...prev, data.data]);
        setStats(prev => ({ ...prev, ...data.stats }));
        setCurrentAction(data.data.message);
      } else if (data.type === 'lead') {
        setStreamedLeads(prev => [data.data, ...prev]);
        setStats(prev => ({ ...prev, ...data.stats }));
      } else if (data.type === 'lead_update') {
        setStreamedLeads(prev => prev.map(l => l.name === data.data.name ? data.data : l));
        setStats(prev => ({ ...prev, ...data.stats }));
      } else if (data.type === 'stats') {
        setStats(prev => ({ ...prev, ...data.stats }));
      }

      // If scan completes, refetch repository and search history
      if (data.stats && data.stats.state !== 'ACTIVE') {
        setIsScanning(false);
        fetchRepository();
        fetchSearchHistory();
      }
    };

    source.onerror = () => {
      console.warn('SSE connection lost. Reconnecting...');
    };
  };

  // Load leads of a past search
  const handleLoadPastSearch = async (task_id, niche, city, country) => {
    setCurrentAction(`Loading results for '${niche}' in '${city}'...`);
    setStats({
      state: 'COMPLETED',
      niche,
      city,
      country,
      entities: 0,
      contacts: 0
    });
    setStreamedLeads([]);
    setActiveTab('Results');

    try {
      const resp = await fetch(`${apiBaseUrl}/history/${task_id}/leads`);
      if (resp.ok) {
        const data = await resp.json();
        setStreamedLeads(data);
        const contactsCount = data.filter(l => l.phone || l.email).length;
        setStats({
          state: 'COMPLETED',
          niche,
          city,
          country,
          entities: data.length,
          contacts: contactsCount
        });
      } else {
        throw new Error('Failed to load past search');
      }
    } catch (err) {
      console.warn('Backend offline or leads not found on server. Checking localStorage.');
      const localLeads = localStorage.getItem(`leads_${task_id}`);
      if (localLeads) {
        const data = JSON.parse(localLeads);
        setStreamedLeads(data);
        const contactsCount = data.filter(l => l.phone || l.email).length;
        setStats({
          state: 'COMPLETED',
          niche,
          city,
          country,
          entities: data.length,
          contacts: contactsCount
        });
      } else {
        alert('Leads file could not be found locally or on the server.');
      }
    }
  };

  // Stop search execution
  const handleStopSearch = async () => {
    setActiveTab('Results');
    if (settings.mockModeForce || !isScanning) {
      if (mockIntervalRef.current) {
        clearInterval(mockIntervalRef.current);
        mockIntervalRef.current = null;
      }
      setIsScanning(false);
      setStats(prev => ({ ...prev, state: 'COMPLETED' }));
      
      const newLeads = [...streamedLeads].map(l => ({
        ...l,
        timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
        status: 'Active'
      }));

      setRepository(prev => {
        const merged = [...newLeads, ...prev];
        const deduped = [];
        const seen = new Set();
        for (const item of merged) {
          const name = item.name.toLowerCase();
          if (!seen.has(name)) {
            seen.add(name);
            deduped.push(item);
          }
        }
        localStorage.setItem('lead_repository', JSON.stringify(deduped));
        return deduped;
      });

      // Save mock history entry
      const taskId = `mock-task-${Date.now()}`;
      const newHistoryEntry = {
        id: taskId,
        niche: stats.niche,
        city: stats.city,
        country: stats.country,
        timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
        sources: ['google_maps'],
        entities_discovered: newLeads.length,
        contacts_verified: newLeads.filter(l => l.phone || l.email).length,
        status: 'COMPLETED'
      };

      localStorage.setItem(`leads_${taskId}`, JSON.stringify(newLeads));
      setSearchHistory(prev => {
        const updated = [newHistoryEntry, ...prev];
        localStorage.setItem('search_history', JSON.stringify(updated));
        return updated;
      });
      
      setCurrentAction("Search execution stopped by user. Gathered results loaded.");
      return;
    }

    try {
      await fetch(`${apiBaseUrl}/search/stop`, {
        method: 'POST'
      });
      setCurrentAction("Stopping search engine... compiling results...");
    } catch (err) {
      console.warn("Error stopping search:", err);
    }
  };

  // Start search (trigger API call or run Mock mode if backend offline)
  const handleStartSearch = async (searchParams) => {
    setLogs([]);
    setStreamedLeads([]);
    setCurrentAction('Initializing scan...');
    setStats({
      state: 'ACTIVE',
      niche: searchParams.niche,
      city: searchParams.city,
      country: searchParams.country,
      entities: 0,
      contacts: 0
    });
    setIsScanning(true);
    setActiveTab('Intelligence');

    if (settings.mockModeForce) {
      console.info('Forcing mock scraping mode.');
      runMockScraping(searchParams);
      return;
    }

    try {
      const resp = await fetch(`${apiBaseUrl}/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(searchParams)
      });
      
      if (resp.ok) {
        setTimeout(setupEventSource, 200);
      } else {
        const errorData = await resp.json();
        alert(`Search error: ${errorData.message}`);
        setIsScanning(false);
      }
    } catch (err) {
      console.warn('Backend offline. Initiating mock scraping session.');
      runMockScraping(searchParams);
    }
  };

  // Mock scraper execution for standalone front-end mode
  const runMockScraping = (params) => {
    let step = 0;
    const workerCount = params.worker_count || 6;
    const targetLeads = params.target_leads || 20;

    // Generate search query buckets for W workers in the mock session
    const prefixes = ["luxury", "best", "affordable", "top", "local", "commercial", "residential", "professional", "custom", "contractor"];
    const queries = [];
    for (let i = 0; i < workerCount; i++) {
      if (i === 0) {
        queries.push(`${params.niche} ${params.city}`);
      } else if (i < prefixes.length + 1) {
        queries.push(`${prefixes[i-1]} ${params.niche} ${params.city}`);
      } else {
        queries.push(`${params.niche} ${i} ${params.city}`);
      }
    }

    // Initialize mock workers_activity
    const mockWorkersActivity = {};
    for (let i = 0; i < workerCount; i++) {
      mockWorkersActivity[`Worker ${i+1}`] = {
        status: 'Searching',
        query: queries[i],
        leads_found: 0,
        websites_verified: 0,
        emails_extracted: 0,
        phones_extracted: 0,
        search_time: 0,
        start_time: Date.now() / 1000
      };
    }

    const mockLogs = [
      { time: 0, message: `System initialized with ${workerCount} parallel workers. Connection to intelligence nodes established.`, is_success: true },
      { time: 1, message: `Semantic expansion: Synonyms, alternate naming generated for '${params.niche}'.`, is_success: false },
      { time: 2, message: `Query vector: Searching Google Maps index for ${params.city}, ${params.country}...`, is_success: false },
      { time: 3, message: "Ingesting Google Maps listings...", is_success: false },
      { time: 4, message: "Query vector: Searching Yellow Pages / Yelp directory...", is_success: false },
      { time: 5, message: "Processing data rows: verifying websites and extracting digital contact metadata...", is_success: false },
      { time: 6, message: "Query vector: Searching social graph connections via Instagram & Facebook...", is_success: false },
      { time: 7, message: "Post-processing: De-duplicating records using SEQUENCE metrics...", is_success: false },
      { time: 8, message: "Filtering: segmenting leads without a business website...", is_success: false },
      { time: 9, message: "Saving records: Writing CSV and Excel worksheets to repository.", is_success: true }
    ];

    const mockLeadsList = [
      { 
        name: "Acme Corp", 
        category: params.niche, 
        score: 98.0, 
        address: `${params.city}, ${params.country}`, 
        phone: "+1 555-0198", 
        email: "j.doe@acme.io", 
        website: "acme.io", 
        source: "google_maps",
        website_exists: true,
        website_opportunity_score: 40,
        website_tier: "Tier B", // Good Website
        country: params.country || "United States",
        city: params.city,
        area: "Downtown",
        website_checks: { ssl: true, responsive: true, contact: true, seo: false, outdated: false, social: true, branding: true }
      },
      { 
        name: "Globex Dynamics", 
        category: params.niche, 
        score: 94.0, 
        address: `${params.city}, ${params.country}`, 
        phone: "+1 555-0245", 
        email: "s.connor@globex.net", 
        website: "globex.net", 
        source: "facebook",
        website_exists: true,
        website_opportunity_score: 10,
        website_tier: "Tier A", // Exceptional Website
        country: params.country || "United States",
        city: params.city,
        area: "Business Hub",
        website_checks: { ssl: true, responsive: true, contact: true, seo: true, outdated: false, social: true, branding: true }
      },
      { 
        name: "Initech Solutions", 
        category: params.niche, 
        score: 75.0, 
        address: `${params.city}, ${params.country}`, 
        phone: "+1 555-0892", 
        email: "m.bolton@initech.co", 
        website: "initech.co", 
        source: "yellowpages",
        website_exists: true,
        website_opportunity_score: 75,
        website_tier: "Tier C", // Poor Website
        country: params.country || "United States",
        city: params.city,
        area: "Commercial Zone",
        website_checks: { ssl: false, responsive: false, contact: true, seo: false, outdated: true, social: false, branding: false }
      },
      { 
        name: "Soylent Corp", 
        category: params.niche, 
        score: 65.0, 
        address: `${params.city}, ${params.country}`, 
        phone: "+1 555-0112", 
        email: "r.thorn@soylent.io", 
        website: "soylent.io", 
        source: "instagram",
        website_exists: true,
        website_opportunity_score: 95,
        website_tier: "Tier D", // Dead Website
        country: params.country || "United States",
        city: params.city,
        area: "Industrial Zone",
        website_checks: { ssl: false, responsive: false, contact: false, seo: false, outdated: true, social: false, branding: false }
      },
      { 
        name: "Apex Services", 
        category: params.niche, 
        score: 55.0, 
        address: `${params.city}, ${params.country}`, 
        phone: "+1 555-0999", 
        email: "info@apexservices.com", 
        website: "", 
        source: "google_maps",
        website_exists: false,
        website_opportunity_score: 100,
        website_tier: "Tier E", // No Website
        country: params.country || "United States",
        city: params.city,
        area: "Market Square",
        website_checks: { ssl: false, responsive: false, contact: false, seo: false, outdated: true, social: false, branding: false }
      }
    ];

    if (mockIntervalRef.current) clearInterval(mockIntervalRef.current);

    mockIntervalRef.current = setInterval(() => {
      // Create a mutable copy of the workers activity
      const updatedWorkers = { ...mockWorkersActivity };
      
      // Update elapsed search time for active workers
      Object.keys(updatedWorkers).forEach(name => {
        const w = updatedWorkers[name];
        if (w.status !== 'Completed') {
          w.search_time = Math.round((Date.now() / 1000) - w.start_time);
        }
      });

      // Simulate worker actions based on log steps
      if (step === 2) {
        if (updatedWorkers['Worker 1']) {
          updatedWorkers['Worker 1'].leads_found = 1;
          updatedWorkers['Worker 1'].status = 'Verifying Websites';
        }
      } else if (step === 3) {
        if (updatedWorkers['Worker 1']) {
          updatedWorkers['Worker 1'].websites_verified = 1;
          updatedWorkers['Worker 1'].emails_extracted = 1;
          updatedWorkers['Worker 1'].phones_extracted = 1;
          updatedWorkers['Worker 1'].status = 'Extracting Contacts';
        }
        if (updatedWorkers['Worker 2']) {
          updatedWorkers['Worker 2'].leads_found = 1;
          updatedWorkers['Worker 2'].status = 'Verifying Websites';
        }
      } else if (step === 5) {
        if (updatedWorkers['Worker 1']) {
          updatedWorkers['Worker 1'].status = 'Completed';
        }
        if (updatedWorkers['Worker 2']) {
          updatedWorkers['Worker 2'].websites_verified = 1;
          updatedWorkers['Worker 2'].emails_extracted = 1;
          updatedWorkers['Worker 2'].phones_extracted = 1;
          updatedWorkers['Worker 2'].status = 'Completed';
        }
        if (updatedWorkers['Worker 3']) {
          updatedWorkers['Worker 3'].leads_found = 2;
          updatedWorkers['Worker 3'].status = 'Extracting Contacts';
        }
      } else if (step === 7) {
        Object.keys(updatedWorkers).forEach((name, idx) => {
          updatedWorkers[name].status = 'Completed';
          if (idx === 2) {
            updatedWorkers[name].websites_verified = 2;
            updatedWorkers[name].emails_extracted = 2;
            updatedWorkers[name].phones_extracted = 2;
          }
        });
      }

      if (step < mockLogs.length) {
        const log = mockLogs[step];
        setLogs(prev => [...prev, log]);
        setCurrentAction(log.message);

        // Add mock leads along the way
        if (step === 3) {
          setStreamedLeads(prev => [mockLeadsList[0], ...prev]);
          setStats(prev => ({
            ...prev,
            entities: 1,
            contacts: 1,
            companies_found: 3,
            websites_verified: 2,
            emails_extracted: 1,
            phones_extracted: 1,
            duplicates_removed: 1,
            no_website_leads: 0,
            poor_website_leads: 0,
            lead_quality_avg: 98.0,
            active_workers: Math.max(0, workerCount - 1),
            search_progress: 25,
            workers_activity: updatedWorkers
          }));
        } else if (step === 5) {
          setStreamedLeads(prev => [mockLeadsList[1], mockLeadsList[2], ...prev]);
          setStats(prev => ({
            ...prev,
            entities: 3,
            contacts: 3,
            companies_found: 6,
            websites_verified: 4,
            emails_extracted: 2,
            phones_extracted: 2,
            duplicates_removed: 2,
            no_website_leads: 0,
            poor_website_leads: 1, // Initech
            lead_quality_avg: 89.0,
            active_workers: Math.max(0, workerCount - 2),
            search_progress: 50,
            workers_activity: updatedWorkers
          }));
        } else if (step === 7) {
          setStreamedLeads(prev => [mockLeadsList[3], mockLeadsList[4], ...prev]);
          setStats(prev => ({
            ...prev,
            entities: 5,
            contacts: 5,
            companies_found: 10,
            websites_verified: 8,
            emails_extracted: 4,
            phones_extracted: 4,
            duplicates_removed: 3,
            no_website_leads: 1, // Apex Services
            poor_website_leads: 2, // Initech + Soylent (Tier D)
            lead_quality_avg: 77.2,
            active_workers: 0,
            search_progress: 100,
            workers_activity: updatedWorkers
          }));
        } else {
          setStats(prev => ({
            ...prev,
            active_workers: Math.max(0, workerCount - step),
            workers_activity: updatedWorkers
          }));
        }
        
        step++;
      } else {
        clearInterval(mockIntervalRef.current);
        setIsScanning(false);
        
        // Finalize workers activity copy
        Object.keys(updatedWorkers).forEach(name => {
          updatedWorkers[name].status = 'Completed';
        });

        setStats(prev => ({
          ...prev,
          state: 'COMPLETED',
          active_workers: 0,
          search_progress: 100,
          workers_activity: updatedWorkers
        }));
        
        const timestampStr = new Date().toISOString().replace('T', ' ').substring(0, 19);
        // Append mock results to local repository
        const newLeads = mockLeadsList.map(l => ({
          ...l,
          timestamp: timestampStr,
          status: 'Active'
        }));

        setRepository(prev => {
          const merged = [...newLeads, ...prev];
          const deduped = [];
          const seen = new Set();
          for (const item of merged) {
            const name = item.name.toLowerCase();
            if (!seen.has(name)) {
              seen.add(name);
              deduped.push(item);
            }
          }
          localStorage.setItem('lead_repository', JSON.stringify(deduped));
          return deduped;
        });

        // Save mock history entry
        const taskId = `mock-task-${Date.now()}`;
        const newHistoryEntry = {
          id: taskId,
          niche: params.niche,
          city: params.city,
          country: params.country,
          timestamp: timestampStr,
          sources: params.sources,
          entities_discovered: newLeads.length,
          contacts_verified: newLeads.filter(l => l.phone || l.email).length,
          status: 'COMPLETED'
        };

        localStorage.setItem(`leads_${taskId}`, JSON.stringify(newLeads));
        setSearchHistory(prev => {
          const updated = [newHistoryEntry, ...prev];
          localStorage.setItem('search_history', JSON.stringify(updated));
          return updated;
        });
      }
    }, 1200);
  };

  // Update repository lead status (Active/Archived)
  const handleUpdateStatus = async (name, newStatus) => {
    setRepository(prev => {
      const updated = prev.map(l => l.name === name ? { ...l, status: newStatus } : l);
      localStorage.setItem('lead_repository', JSON.stringify(updated));
      return updated;
    });

    try {
      await fetch(`${apiBaseUrl}/repository/update-status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, status: newStatus })
      });
    } catch (err) {
      console.warn('Backend offline. Status updated locally.');
    }
  };

  return (
    <>
      {/* Top Navigation AppBar */}
      <header className="header-bar">
        <div className="logo-section" onClick={() => setActiveTab('Search')} style={{ cursor: 'pointer' }}>
          <span className="material-symbols-outlined logo-icon">terminal</span>
          <h1 className="logo-text">LeadIntel</h1>
          <span className="logo-version">Terminal v1.0</span>
        </div>

        <nav className="nav-links">
          <button
            className={`nav-item ${activeTab === 'Search' ? 'active' : ''}`}
            onClick={() => setActiveTab('Search')}
          >
            <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>
              search
            </span>
            Search
          </button>
          <button
            className={`nav-item ${activeTab === 'Intelligence' ? 'active' : ''}`}
            onClick={() => setActiveTab('Intelligence')}
          >
            <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>
              radar
            </span>
            Intelligence
          </button>
          <button
            className={`nav-item ${activeTab === 'Results' ? 'active' : ''}`}
            onClick={() => setActiveTab('Results')}
          >
            <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>
              stream
            </span>
            Results
          </button>
          <button
            className={`nav-item ${activeTab === 'Repository' ? 'active' : ''}`}
            onClick={() => setActiveTab('Repository')}
          >
            <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>
              folder_shared
            </span>
            Repository
          </button>
        </nav>

        <div className="action-section">
          {isScanning ? (
            <button
              className="btn-primary"
              onClick={handleStopSearch}
              style={{ backgroundColor: '#EF4444', color: '#FFFFFF' }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>
                stop
              </span>
              Stop Scan
            </button>
          ) : (
            <button
              className="btn-primary"
              onClick={() => {
                setActiveTab('Search');
              }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>
                add
              </span>
              New Scan
            </button>
          )}
          <div className="divider-v"></div>
          <button className="icon-btn" title="Settings" onClick={() => setShowSettingsModal(true)}>
            <span className="material-symbols-outlined" style={{ fontSize: '20px' }}>
              settings
            </span>
          </button>
          <button className="icon-btn" title="Help" onClick={() => setShowHelpModal(true)}>
            <span className="material-symbols-outlined" style={{ fontSize: '20px' }}>
              help_outline
            </span>
          </button>
          <img
            src="https://lh3.googleusercontent.com/aida-public/AB6AXuD81RQV6xADJcA8HZDe4iOIrVGkzzKz3kXA5ZlRcIP1yaNs9-oeFc_XPN7rtecBSb68hhVzM-lOzW3JP8xUVqCdnc23gWA8kF0x1ihcUxWRYJHDvL8Ijvyaxb8kZ10q6h1Dr6F7mEu8DdcDmktf0f2RmNLjt3648f30blx2zJvkxcS4YFofRZOz-vfqZgp9q9_KDsX8-SvTOL6MszFK8J5mn48TMEcEYvDT_Wv_xJfrjUP6ghR2k1I8lmH7vXWdO1mr7--Q88JIFpBx"
            alt="Admin"
            className="avatar-img"
          />
        </div>
      </header>

      {/* Main Viewport Container */}
      <div className="main-viewport">
        {/* Animated Scan Line Overlay */}
        {isScanning && <div className="scan-overlay-line"></div>}

        <main className="canvas-container">
          {activeTab === 'Search' && (
            <SearchWorkspace
              onStartSearch={handleStartSearch}
              isScanning={isScanning}
              searchHistory={searchHistory}
              onLoadPastSearch={handleLoadPastSearch}
            />
          )}

          {activeTab === 'Intelligence' && (
            <LiveIntelligence
              logs={logs}
              stats={stats}
              currentAction={currentAction}
              onStopSearch={handleStopSearch}
            />
          )}

          {activeTab === 'Results' && (
            <ResultsStream
              leads={streamedLeads}
              state={stats.state}
            />
          )}

          {activeTab === 'Repository' && (
            <LeadRepository
              repository={repository}
              onUpdateStatus={handleUpdateStatus}
            />
          )}

          {/* Grid Background Effect */}
          <div className="grid-bg-overlay"></div>
        </main>
      </div>

      {/* Settings Modal */}
      {showSettingsModal && (
        <div className="modal-overlay" onClick={() => setShowSettingsModal(false)}>
          <div className="modal-container" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3 className="modal-title">System Configuration & Settings</h3>
              <button className="modal-close-btn" onClick={() => setShowSettingsModal(false)}>
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>
            <div className="modal-body">
              <div className="settings-group">
                <label className="settings-label">FastAPI Endpoint URL</label>
                <input
                  type="text"
                  className="settings-input"
                  value={apiBaseUrl}
                  onChange={(e) => setApiBaseUrl(e.target.value)}
                  placeholder="e.g. http://127.0.0.1:8000/api"
                />
              </div>

              <div className="settings-group">
                <label className="settings-label">Default Scraping Limit</label>
                <select
                  className="settings-select"
                  value={settings.defaultMaxResults}
                  onChange={(e) => setSettings(prev => ({ ...prev, defaultMaxResults: parseInt(e.target.value, 10) }))}
                >
                  <option value="10">10 Leads</option>
                  <option value="30">30 Leads</option>
                  <option value="50">50 Leads</option>
                  <option value="100">100 Leads</option>
                  <option value="200">200 Leads</option>
                </select>
              </div>

              <div className="settings-group" style={{ marginTop: '8px' }}>
                <label className="settings-switch-label">
                  <input
                    type="checkbox"
                    className="settings-switch-input"
                    checked={settings.mockModeForce}
                    onChange={(e) => setSettings(prev => ({ ...prev, mockModeForce: e.target.checked }))}
                  />
                  Force Standalone Sandbox Mode (Mock Scrapers)
                </label>
              </div>

              <div className="settings-group" style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid var(--outline)' }}>
                <label className="settings-label">Network Status</label>
                <div className="system-status-pills">
                  <span className="status-badge" style={{ borderColor: 'rgba(16, 185, 129, 0.3)', color: 'var(--primary-accent)' }}>
                    <span className="status-indicator"></span>
                    API Server Connected
                  </span>
                  <span className="status-badge">
                    Active Scraper Engines: 4
                  </span>
                  <span className="status-badge">
                    Environment: Production
                  </span>
                </div>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn-secondary" onClick={() => setShowSettingsModal(false)}>
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Help Modal */}
      {showHelpModal && (
        <div className="modal-overlay" onClick={() => setShowHelpModal(false)}>
          <div className="modal-container" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3 className="modal-title">LeadIntel User Guide & Reference</h3>
              <button className="modal-close-btn" onClick={() => setShowHelpModal(false)}>
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>
            <div className="modal-body">
              <div className="help-section">
                <h4 className="help-section-title">Search Intelligence Engine</h4>
                <p className="help-text">
                  LeadIntel is an elite lead discovery system that finds active businesses lacking websites. It performs semantic expansion across synonyms, regional abbreviations, and business types to yield maximum lookup precision.
                </p>
              </div>

              <div className="help-section">
                <h4 className="help-section-title">Data Channels & Platforms</h4>
                <p className="help-text">
                  Choose from 4 scraping engines to capture leads:
                </p>
                <ul className="help-list">
                  <li className="help-list-item">🗺️ <strong>Google Maps</strong>: Primary source for local listing verification.</li>
                  <li className="help-list-item">📒 <strong>Yellow Pages / Yelp</strong>: Gathers address directories.</li>
                  <li className="help-list-item">📸 <strong>Instagram</strong>: Extracts social graph bios and metadata.</li>
                  <li className="help-list-item">📘 <strong>Facebook</strong>: Queries page details and contact emails.</li>
                </ul>
              </div>

              <div className="help-section">
                <h4 className="help-section-title">Search History & Reloading</h4>
                <p className="help-text">
                  All completed searches are cataloged under the "Recent Searches" panel in the Search Workspace. Click <strong>Load Results</strong> on any past query to fetch its specific lead set and review it instantly in the Results tab.
                </p>
              </div>

              <div className="help-section">
                <h4 className="help-section-title">Exporting Leads</h4>
                <p className="help-text">
                  Navigate to the <strong>Repository</strong> tab to sort/filter your global leads database, change status metrics (Active vs. Archived), or export everything to a formatted UTF-8 CSV spreadsheet.
                </p>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn-secondary" onClick={() => setShowHelpModal(false)}>
                Close Guide
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
