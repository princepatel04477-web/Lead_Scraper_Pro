import React, { useState } from 'react';

export default function SearchWorkspace({ onStartSearch, isScanning, searchHistory = [], onLoadPastSearch }) {
  const [niche, setNiche] = useState('');
  const [city, setCity] = useState('');
  const [country, setCountry] = useState('');
  const [useGmaps, setUseGmaps] = useState(true);
  const [useYp, setUseYp] = useState(true);
  const [useInsta, setUseInsta] = useState(false);
  const [useFb, setUseFb] = useState(false);
  const [targetLeads, setTargetLeads] = useState(20);
  const [workerCount, setWorkerCount] = useState(6);
  const [broaden, setBroaden] = useState(true);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!niche || !city) {
      alert('Please fill in Niche and City.');
      return;
    }

    const sources = [];
    if (useGmaps) sources.push('google_maps');
    if (useYp) sources.push('yellowpages');
    if (useInsta) sources.push('instagram');
    if (useFb) sources.push('facebook');

    if (sources.length === 0) {
      alert('Please select at least one data source.');
      return;
    }

    onStartSearch({
      niche,
      city,
      country,
      sources,
      max_results: parseInt(targetLeads, 10),
      target_leads: parseInt(targetLeads, 10),
      worker_count: parseInt(workerCount, 10),
      broaden,
      headless: true
    });
  };

  return (
    <div className="search-center-box">
      <div className="search-title-sec fade-in-up">
        <h2 className="search-title">Find businesses before everyone else.</h2>
        <p className="search-subtitle">System Ready // Awaiting Input</p>
      </div>

      <form onSubmit={handleSubmit} className="search-panel fade-in-up delay-100">
        <div className="search-fields-row">
          <div className="field-group">
            <label className="field-label">Niche</label>
            <input
              type="text"
              value={niche}
              onChange={(e) => setNiche(e.target.value)}
              className="input-text"
              placeholder="e.g. AI Startups, Real Estate"
              disabled={isScanning}
            />
          </div>
          <div className="field-group">
            <label className="field-label">City</label>
            <input
              type="text"
              value={city}
              onChange={(e) => setCity(e.target.value)}
              className="input-text"
              placeholder="e.g. San Francisco"
              disabled={isScanning}
            />
          </div>
          <div className="field-group">
            <label className="field-label">Country</label>
            <input
              type="text"
              value={country}
              onChange={(e) => setCountry(e.target.value)}
              className="input-text"
              placeholder="e.g. United States"
              disabled={isScanning}
            />
          </div>
        </div>

        <div className="checkbox-group">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={useGmaps}
              onChange={(e) => setUseGmaps(e.target.checked)}
              className="checkbox-input"
              disabled={isScanning}
            />
            🗺️ Google Maps
          </label>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={useYp}
              onChange={(e) => setUseYp(e.target.checked)}
              className="checkbox-input"
              disabled={isScanning}
            />
            📒 Yellow Pages
          </label>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={useInsta}
              onChange={(e) => setUseInsta(e.target.checked)}
              className="checkbox-input"
              disabled={isScanning}
            />
            📸 Instagram
          </label>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={useFb}
              onChange={(e) => setUseFb(e.target.checked)}
              className="checkbox-input"
              disabled={isScanning}
            />
            📘 Facebook
          </label>
          <label className="checkbox-label" style={{ marginLeft: 'auto' }}>
            <span style={{ fontSize: '10px' }}>Target Leads:</span>
            <select
              value={targetLeads}
              onChange={(e) => setTargetLeads(e.target.value)}
              style={{
                background: 'transparent',
                border: 'none',
                borderBottom: '1px solid var(--outline)',
                color: 'var(--text-primary)',
                marginLeft: '4px',
                fontSize: '11px',
                fontFamily: 'var(--font-mono)'
              }}
              disabled={isScanning}
            >
              <option value="20" style={{background: '#090909'}}>20 Leads</option>
              <option value="50" style={{background: '#090909'}}>50 Leads</option>
              <option value="100" style={{background: '#090909'}}>100 Leads</option>
              <option value="250" style={{background: '#090909'}}>250 Leads</option>
              <option value="500" style={{background: '#090909'}}>500 Leads</option>
            </select>
          </label>
          <label className="checkbox-label" style={{ marginLeft: '12px' }}>
            <span style={{ fontSize: '10px' }}>Worker Count:</span>
            <select
              value={workerCount}
              onChange={(e) => setWorkerCount(e.target.value)}
              style={{
                background: 'transparent',
                border: 'none',
                borderBottom: '1px solid var(--outline)',
                color: 'var(--text-primary)',
                marginLeft: '4px',
                fontSize: '11px',
                fontFamily: 'var(--font-mono)'
              }}
              disabled={isScanning}
            >
              {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map(n => (
                <option key={n} value={n} style={{background: '#090909'}}>{n} Workers</option>
              ))}
            </select>
          </label>
        </div>

        <div className="search-submit-row">
          <button
            type="submit"
            className="btn-execute"
            disabled={isScanning}
            style={{ opacity: isScanning ? 0.5 : 1 }}
          >
            {isScanning ? 'Scanning...' : 'Execute Search'}
            <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>
              arrow_forward
            </span>
          </button>
        </div>
      </form>

      <div className="search-status-bar fade-in-up delay-200">
        <span className="status-badge">
          <span className="status-indicator"></span>
          Status: Online
        </span>
        <span className="status-badge">
          <span className="material-symbols-outlined" style={{ fontSize: '14px' }}>
            database
          </span>
          Index: 4.2B Nodes
        </span>
      </div>

      {/* Search History Section */}
      {searchHistory.length > 0 && (
        <div className="history-sec fade-in-up delay-300">
          <div className="history-sec-header">
            <h3 className="history-sec-title">Recent Searches // History Logs</h3>
          </div>
          <div className="history-grid">
            {searchHistory.map((item) => (
              <div key={item.id} className="history-card">
                <div className="history-card-header">
                  <div>
                    <h4 className="history-card-niche" style={{ margin: 0, fontSize: '15px' }}>{item.niche}</h4>
                    <div className="history-card-location" style={{ marginTop: '4px' }}>
                      <span className="material-symbols-outlined" style={{ fontSize: '14px', verticalAlign: 'middle', marginRight: '4px' }}>
                        location_on
                      </span>
                      {item.city}, {item.country}
                    </div>
                  </div>
                  <span className={`history-stat-tag ${item.status === 'COMPLETED' ? 'success' : item.status === 'ACTIVE' ? 'active' : 'error'}`}>
                    {item.status}
                  </span>
                </div>
                
                <div className="history-card-stats" style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                  <span className="history-stat-tag">
                    {item.entities_discovered} Discovered
                  </span>
                  <span className="history-stat-tag">
                    {item.contacts_verified} Verified
                  </span>
                </div>

                <div className="history-card-footer">
                  <span className="history-card-time">{item.timestamp}</span>
                  <button
                    type="button"
                    className="btn-history-load"
                    onClick={() => onLoadPastSearch(item.id, item.niche, item.city, item.country)}
                    disabled={isScanning || item.status === 'ACTIVE'}
                    style={{ opacity: (isScanning || item.status === 'ACTIVE') ? 0.5 : 1 }}
                  >
                    Load Results
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
