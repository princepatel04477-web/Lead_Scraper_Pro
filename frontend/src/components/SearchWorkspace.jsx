import React, { useState } from 'react';

export default function SearchWorkspace({ onStartSearch, isScanning }) {
  const [niche, setNiche] = useState('');
  const [city, setCity] = useState('');
  const [country, setCountry] = useState('');
  const [useGmaps, setUseGmaps] = useState(true);
  const [useYp, setUseYp] = useState(true);
  const [useInsta, setUseInsta] = useState(false);
  const [useFb, setUseFb] = useState(false);
  const [maxResults, setMaxResults] = useState(50);
  const [broaden, setBroaden] = useState(true);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!niche || !city || !country) {
      alert('Please fill in Niche, City, and Country.');
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
      max_results: parseInt(maxResults, 10),
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
            <span style={{ fontSize: '10px' }}>Max:</span>
            <select
              value={maxResults}
              onChange={(e) => setMaxResults(e.target.value)}
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
              <option value="10" style={{background: '#090909'}}>10</option>
              <option value="30" style={{background: '#090909'}}>30</option>
              <option value="50" style={{background: '#090909'}}>50</option>
              <option value="100" style={{background: '#090909'}}>100</option>
              <option value="200" style={{background: '#090909'}}>200</option>
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
    </div>
  );
}
