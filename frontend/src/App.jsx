import React, { useState, useEffect, useRef } from 'react';
import SearchWorkspace from './components/SearchWorkspace';
import LiveIntelligence from './components/LiveIntelligence';
import ResultsStream from './components/ResultsStream';
import LeadRepository from './components/LeadRepository';

const API_BASE = 'http://127.0.0.1:8000/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('Search');
  const [isScanning, setIsScanning] = useState(false);
  const [currentAction, setCurrentAction] = useState('');
  
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
  
  const eventSourceRef = useRef(null);
  const mockIntervalRef = useRef(null);

  // Fetch repository leads
  const fetchRepository = async () => {
    try {
      const resp = await fetch(`${API_BASE}/repository`);
      if (resp.ok) {
        const data = await resp.json();
        setRepository(data);
      }
    } catch (err) {
      console.warn('Backend offline. Using local storage or mock repository.');
      // Load from localStorage if available
      const localRepo = localStorage.getItem('lead_repository');
      if (localRepo) {
        setRepository(JSON.parse(localRepo));
      } else {
        // Fallback mockup seeds
        const mockSeeds = [
          { name: "Aura Quantum", category: "Deep Tech", score: 92.0, status: "Active", address: "Boston, MA", phone: "+1 617-555-0143", email: "contact@auraq.io", website: "auraq.io" },
          { name: "Vortex Dynamics", category: "Logistics", score: 85.0, status: "Active", address: "Dallas, TX", phone: "+1 214-555-0198", email: "ops@vortexdyn.com", website: "vortexdyn.com" },
          { name: "Nexo Robotics", category: "Automation", score: 78.0, status: "Archived", address: "Detroit, MI", phone: "+1 313-555-0182", email: "info@nexorobotics.com", website: "nexorobotics.com" },
          { name: "Synapse Labs", category: "Biotech", score: 88.0, status: "Active", address: "Seattle, WA", phone: "+1 206-555-0129", email: "research@synapselabs.org", website: "synapselabs.org" }
        ];
        setRepository(mockSeeds);
        localStorage.setItem('lead_repository', JSON.stringify(mockSeeds));
      }
    }
  };

  // Sync state with backend on startup
  useEffect(() => {
    fetchRepository();

    const checkState = async () => {
      try {
        const resp = await fetch(`${API_BASE}/state`);
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
  }, []);

  // Connect to SSE stream
  const setupEventSource = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const source = new EventSource(`${API_BASE}/stream`);
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
          contacts: data.contacts
        });
        setIsScanning(data.state === 'ACTIVE');
      } else if (data.type === 'log') {
        setLogs(prev => [...prev, data.data]);
        setStats(prev => ({ ...prev, ...data.stats }));
        setCurrentAction(data.data.message);
      } else if (data.type === 'lead') {
        setStreamedLeads(prev => [data.data, ...prev]);
        setStats(prev => ({ ...prev, ...data.stats }));
      }

      // If scan completes, refetch repository
      if (data.stats && data.stats.state !== 'ACTIVE') {
        setIsScanning(false);
        fetchRepository();
      }
    };

    source.onerror = () => {
      console.warn('SSE connection lost. Reconnecting...');
    };
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

    try {
      const resp = await fetch(`${API_BASE}/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(searchParams)
      });
      
      if (resp.ok) {
        // SSE connection
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
    const mockLogs = [
      { time: 0, message: "System initialized. Connection to intelligence nodes established.", is_success: true },
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
      { name: "Acme Corp", category: params.niche, score: 98.4, address: `${params.city}, ${params.country}`, phone: "+1 555-0198", email: "j.doe@acme.io", website: "acme.io" },
      { name: "Globex Dynamics", category: params.niche, score: 94.1, address: `${params.city}, ${params.country}`, phone: "+1 555-0245", email: "s.connor@globex.net", website: "globex.net" },
      { name: "Initech Solutions", category: params.niche, score: 89.7, address: `${params.city}, ${params.country}`, phone: "+1 555-0892", email: "m.bolton@initech.co", website: "initech.co" },
      { name: "Soylent Corp", category: params.niche, score: 82.3, address: `${params.city}, ${params.country}`, phone: "+1 555-0112", email: "r.thorn@soylent.io", website: "soylent.io" }
    ];

    if (mockIntervalRef.current) clearInterval(mockIntervalRef.current);

    mockIntervalRef.current = setInterval(() => {
      if (step < mockLogs.length) {
        const log = mockLogs[step];
        setLogs(prev => [...prev, log]);
        setCurrentAction(log.message);

        // Add some mock leads along the way
        if (step === 3) {
          setStreamedLeads(prev => [mockLeadsList[0], ...prev]);
          setStats(prev => ({ ...prev, entities: 1, contacts: 1 }));
        } else if (step === 5) {
          setStreamedLeads(prev => [mockLeadsList[1], ...prev]);
          setStats(prev => ({ ...prev, entities: 2, contacts: 2 }));
        } else if (step === 7) {
          setStreamedLeads(prev => [mockLeadsList[2], mockLeadsList[3], ...prev]);
          setStats(prev => ({ ...prev, entities: 4, contacts: 4 }));
        }
        
        step++;
      } else {
        clearInterval(mockIntervalRef.current);
        setIsScanning(false);
        setStats(prev => ({ ...prev, state: 'COMPLETED' }));
        
        // Append mock results to local repository
        const newLeads = mockLeadsList.map(l => ({
          ...l,
          timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
          status: 'Active'
        }));

        setRepository(prev => {
          const merged = [...newLeads, ...prev];
          // Deduplicate by name
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
      }
    }, 2000);
  };

  // Update repository lead status (Active/Archived)
  const handleUpdateStatus = async (name, newStatus) => {
    // Optimistic UI update
    setRepository(prev => {
      const updated = prev.map(l => l.name === name ? { ...l, status: newStatus } : l);
      localStorage.setItem('lead_repository', JSON.stringify(updated));
      return updated;
    });

    try {
      await fetch(`${API_BASE}/repository/update-status`, {
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
        <div className="logo-section">
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
          <button
            className="btn-primary"
            onClick={() => {
              setActiveTab('Search');
            }}
            disabled={isScanning}
          >
            <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>
              add
            </span>
            New Scan
          </button>
          <div className="divider-v"></div>
          <button className="icon-btn" title="Settings">
            <span className="material-symbols-outlined" style={{ fontSize: '20px' }}>
              settings
            </span>
          </button>
          <button className="icon-btn" title="Help">
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
            />
          )}

          {activeTab === 'Intelligence' && (
            <LiveIntelligence
              logs={logs}
              stats={stats}
              currentAction={currentAction}
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
    </>
  );
}
