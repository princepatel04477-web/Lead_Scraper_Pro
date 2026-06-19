import React, { useEffect, useRef, useState } from 'react';

export default function LiveIntelligence({ logs, stats, currentAction, onStopSearch }) {
  const [latencyBars, setLatencyBars] = useState([]);
  const [latencyVal, setLatencyVal] = useState(24);
  const logsEndRef = useRef(null);

  // Auto-scroll logs to bottom
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  // Animate mock latency graph
  useEffect(() => {
    // Initialize bars
    const initialBars = Array.from({ length: 30 }, () => Math.random() * 40 + 10);
    setLatencyBars(initialBars);

    const interval = setInterval(() => {
      setLatencyBars(prev => {
        const next = [...prev.slice(1)];
        const newHeight = Math.random() * 80 + 20;
        next.push(newHeight);
        setLatencyVal(Math.floor(newHeight / 2) + 10);
        return next;
      });
    }, 150);

    return () => clearInterval(interval);
  }, []);

  const workersActivity = stats.workers_activity || {};
  const workerNames = Object.keys(workersActivity).sort((a, b) => {
    const numA = parseInt(a.replace('Worker ', ''), 10);
    const numB = parseInt(b.replace('Worker ', ''), 10);
    return numA - numB;
  });

  const formatTime = (secs) => {
    if (!secs) return '0s';
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return m > 0 ? `${m}m ${s}s` : `${s}s`;
  };

  return (
    <div className="live-layout">
      {/* Left Column: Stats & Bento Cards */}
      <div className="left-panel">
        <div className="bento-card" style={{ minHeight: '120px' }}>
          <div className="bento-header">
            <div>
              <h2 className="bento-label">Execution State</h2>
              <p className="bento-title">
                <span className="pulse-node" style={{ backgroundColor: stats.state === 'ACTIVE' ? 'var(--primary-accent)' : 'var(--text-dim)' }}></span>
                {stats.state === 'ACTIVE' ? 'ACTIVE SCAN' : stats.state}
              </p>
              {stats.state === 'ACTIVE' && onStopSearch && (
                <button
                  onClick={onStopSearch}
                  style={{
                    marginTop: '8px',
                    background: 'transparent',
                    border: '1px solid #EF4444',
                    color: '#EF4444',
                    fontSize: '11px',
                    padding: '4px 8px',
                    borderRadius: '2px',
                    cursor: 'pointer',
                    fontFamily: 'var(--font-mono)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                >
                  <span className="material-symbols-outlined" style={{ fontSize: '14px' }}>stop</span>
                  Stop Search
                </button>
              )}
            </div>
            <span className="material-symbols-outlined text-primary-dim">radar</span>
          </div>
          <div className="bento-footer">
            <p className="bento-label">Target Vector</p>
            <p style={{ fontSize: '13px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              {stats.niche ? `${stats.niche} // ${stats.city}` : 'No target selected'}
            </p>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', margin: '10px 0' }}>
          <div className="bento-card" style={{ padding: '10px', height: '80px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <span className="bento-label" style={{ fontSize: '9px', margin: 0 }}>Progress</span>
            <span className="bento-number" style={{ fontSize: '20px' }}>{stats.search_progress || 0}%</span>
            <div style={{ width: '100%', height: '3px', background: 'var(--outline)', borderRadius: '2px', overflow: 'hidden' }}>
              <div style={{ width: `${stats.search_progress || 0}%`, height: '100%', background: 'var(--primary-accent)' }}></div>
            </div>
          </div>

          <div className="bento-card" style={{ padding: '10px', height: '80px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <span className="bento-label" style={{ fontSize: '9px', margin: 0 }}>Active Workers</span>
            <span className="bento-number" style={{ fontSize: '20px' }}>{stats.active_workers || 0}</span>
            <span style={{ fontSize: '9px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>simultaneous</span>
          </div>

          <div className="bento-card" style={{ padding: '10px', height: '80px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <span className="bento-label" style={{ fontSize: '9px', margin: 0 }}>Companies Found</span>
            <span className="bento-number" style={{ fontSize: '20px' }}>{stats.companies_found || 0}</span>
            <span style={{ fontSize: '9px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>raw sweep</span>
          </div>

          <div className="bento-card" style={{ padding: '10px', height: '80px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <span className="bento-label" style={{ fontSize: '9px', margin: 0 }}>Unique Leads</span>
            <span className="bento-number" style={{ fontSize: '20px' }}>{stats.entities || 0}</span>
            <span style={{ fontSize: '9px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>deduplicated</span>
          </div>

          <div className="bento-card" style={{ padding: '10px', height: '80px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <span className="bento-label" style={{ fontSize: '9px', margin: 0 }}>Websites Verified</span>
            <span className="bento-number" style={{ fontSize: '20px' }}>{stats.websites_verified || 0}</span>
            <span style={{ fontSize: '9px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>checks completed</span>
          </div>

          <div className="bento-card" style={{ padding: '10px', height: '80px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <span className="bento-label" style={{ fontSize: '9px', margin: 0 }}>No Website Leads</span>
            <span className="bento-number" style={{ fontSize: '20px', color: '#F87171' }}>{stats.no_website_leads || 0}</span>
            <span style={{ fontSize: '9px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>Tier E (high opp)</span>
          </div>

          <div className="bento-card" style={{ padding: '10px', height: '80px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <span className="bento-label" style={{ fontSize: '9px', margin: 0 }}>Poor Website Leads</span>
            <span className="bento-number" style={{ fontSize: '20px', color: '#FBBF24' }}>{stats.poor_website_leads || 0}</span>
            <span style={{ fontSize: '9px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>Tier C/D (opp)</span>
          </div>

          <div className="bento-card" style={{ padding: '10px', height: '80px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <span className="bento-label" style={{ fontSize: '9px', margin: 0 }}>Emails Extracted</span>
            <span className="bento-number" style={{ fontSize: '20px', color: '#EC4899' }}>{stats.emails_extracted || 0}</span>
            <span style={{ fontSize: '9px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>unique inbox</span>
          </div>

          <div className="bento-card" style={{ padding: '10px', height: '80px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <span className="bento-label" style={{ fontSize: '9px', margin: 0 }}>Phones Extracted</span>
            <span className="bento-number" style={{ fontSize: '20px', color: '#60A5FA' }}>{stats.phones_extracted || 0}</span>
            <span style={{ fontSize: '9px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>lines verified</span>
          </div>

          <div className="bento-card" style={{ padding: '10px', height: '80px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <span className="bento-label" style={{ fontSize: '9px', margin: 0 }}>Duplicates Removed</span>
            <span className="bento-number" style={{ fontSize: '20px', color: '#9CA3AF' }}>{stats.duplicates_removed || 0}</span>
            <span style={{ fontSize: '9px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>global overlap</span>
          </div>

          <div className="bento-card" style={{ padding: '10px', height: '65px', gridColumn: 'span 2', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span className="bento-label" style={{ fontSize: '9px', margin: 0 }}>Lead Quality Average</span>
              <span className="bento-number" style={{ fontSize: '18px', color: 'var(--primary-accent)' }}>{stats.lead_quality_avg || 0}/100</span>
            </div>
            <div style={{ width: '100%', height: '3px', background: 'var(--outline)', borderRadius: '2px', overflow: 'hidden' }}>
              <div style={{ width: `${stats.lead_quality_avg || 0}%`, height: '100%', background: 'var(--primary-accent)' }}></div>
            </div>
          </div>
        </div>

        <div className="bento-card" style={{ padding: '10px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
            <span className="bento-label" style={{ fontSize: '9px', margin: 0 }}>Network Latency</span>
            <span className="bento-label" style={{ color: 'var(--text-primary)', fontSize: '9px', margin: 0 }}>{latencyVal}ms</span>
          </div>
          <div className="latency-graph" style={{ height: '30px', marginTop: '4px' }}>
            {latencyBars.map((height, idx) => (
              <div
                key={idx}
                className="latency-bar"
                style={{ height: `${height}%` }}
              ></div>
            ))}
          </div>
        </div>
      </div>

      {/* Middle Column: Worker Activity Panel */}
      <div className="middle-panel">
        <div className="worker-panel-header">
          <span className="worker-panel-title">Worker Activity Panel</span>
          <span className="worker-time-badge">Active Workers: {workerNames.length}</span>
        </div>
        <div className="worker-list">
          {workerNames.length === 0 ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-dim)', fontSize: '11px', fontFamily: 'var(--font-mono)' }}>
              Awaiting worker allocation...
            </div>
          ) : (
            workerNames.map(name => {
              const w = workersActivity[name];
              const statusClass = w.status.toLowerCase().replace(/\s+/g, '-');
              return (
                <div key={name} className="worker-item">
                  <div className="worker-meta">
                    <span className="worker-name">{name}</span>
                    <span className={`worker-status-badge ${statusClass}`}>
                      {w.status}
                    </span>
                  </div>
                  <div className="worker-meta">
                    <span className="worker-query" title={w.query}>
                      🔍 {w.query}
                    </span>
                    <span className="worker-time-badge">
                      ⏱️ {formatTime(w.search_time)}
                    </span>
                  </div>
                  <div className="worker-stats-grid">
                    <div className="worker-stat">
                      <span className="worker-stat-val">{w.leads_found || 0}</span>
                      <span className="worker-stat-label">Leads</span>
                    </div>
                    <div className="worker-stat">
                      <span className="worker-stat-val">{w.websites_verified || 0}</span>
                      <span className="worker-stat-label">Webs</span>
                    </div>
                    <div className="worker-stat">
                      <span className="worker-stat-val">{w.emails_extracted || 0}</span>
                      <span className="worker-stat-label">Mails</span>
                    </div>
                    <div className="worker-stat">
                      <span className="worker-stat-val">{w.phones_extracted || 0}</span>
                      <span className="worker-stat-label">Phones</span>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Right Column: Terminal Log */}
      <div className="right-panel">
        <div className="terminal-header">
          <span className="terminal-title">Execution Log_</span>
          <div className="terminal-dots">
            <div className="dot"></div>
            <div className="dot"></div>
            <div className="dot"></div>
          </div>
        </div>

        <div className="terminal-logs">
          {logs.length === 0 ? (
            <div className="log-row">
              <span className="log-time">[00:00.00]</span>
              <span>Terminal ready. Awaiting search execution...</span>
            </div>
          ) : (
            logs.map((log, idx) => (
              <div key={idx} className={`log-row ${log.is_success ? 'success' : ''}`}>
                <span className="log-time">
                  [00:{(idx + 1).toString().padStart(2, '0')}.{(idx * 13 % 100).toString().padStart(2, '0')}]
                </span>
                <span>{log.message}</span>
              </div>
            ))
          )}
          <div ref={logsEndRef} />
        </div>

        <div className="terminal-prompt">
          <span style={{ color: 'var(--primary-accent)' }}>&gt;</span>
          <span style={{ flex: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {currentAction || (stats.state === 'ACTIVE' ? 'Processing...' : 'Awaiting data stream...')}
          </span>
          <span className="cursor-blink"></span>
        </div>
      </div>
    </div>
  );
}
