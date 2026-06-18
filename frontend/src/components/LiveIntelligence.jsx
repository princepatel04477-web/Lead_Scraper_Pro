import React, { useEffect, useRef, useState } from 'react';

export default function LiveIntelligence({ logs, stats, currentAction }) {
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

        <div className="bento-grid-2">
          <div className="bento-card" style={{ height: '140px' }}>
            <span className="material-symbols-outlined" style={{ fontSize: '20px', color: 'var(--text-muted)' }}>
              corporate_fare
            </span>
            <div>
              <p className="bento-number">{stats.entities}</p>
              <p className="bento-label">Entities Discovered</p>
            </div>
          </div>

          <div className="bento-card" style={{ height: '140px' }}>
            <span className="material-symbols-outlined" style={{ fontSize: '20px', color: 'var(--text-muted)' }}>
              contact_mail
            </span>
            <div>
              <p className="bento-number">{stats.contacts}</p>
              <p className="bento-label">Contacts Verified</p>
            </div>
          </div>
        </div>

        <div className="bento-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span className="bento-label">Network Latency</span>
            <span className="bento-label" style={{ color: 'var(--text-primary)' }}>{latencyVal}ms</span>
          </div>
          <div className="latency-graph">
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
