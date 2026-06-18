import React from 'react';

export default function ResultsStream({ leads, state }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--stack-lg)', height: '100%', width: '100%' }}>
      {/* Stream Header */}
      <div className="results-header">
        <div>
          <h2 className="results-title">Active Stream</h2>
          <p className="results-subtitle">
            {state === 'ACTIVE' ? 'Ingesting new records in real-time...' : 'Results from the last execution.'}
          </p>
        </div>
        <div className="live-indicator-sec">
          {state === 'ACTIVE' && (
            <div className="pulse-container">
              <div className="pulse-ring"></div>
              <div className="pulse-core"></div>
            </div>
          )}
          <span className="font-label-mono" style={{ color: state === 'ACTIVE' ? 'var(--primary-accent)' : 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 'bold' }}>
            {state === 'ACTIVE' ? 'LIVE' : 'IDLE'}
          </span>
        </div>
      </div>

      {/* List Header */}
      <div className="grid-table-hdr">
        <div>Company</div>
        <div>Contact</div>
        <div>Location</div>
        <div>Digital</div>
        <div style={{ textAlign: 'right' }}>Score</div>
      </div>

      {/* Stream Container */}
      <div className="lead-stream-container">
        {leads.map((lead, idx) => (
          <div key={idx} className="lead-row-card">
            <div className="lead-name-col">
              <span className="lead-name">{lead.name || 'Unknown Company'}</span>
              <span className="lead-sector">{lead.category || 'N/A'}</span>
            </div>

            <div className="lead-contact-col">
              <span className="lead-email">{lead.email || 'N/A'}</span>
              <span className="lead-phone">{lead.phone || 'N/A'}</span>
            </div>

            <div className="lead-location-col">
              <span className="material-symbols-outlined lead-location-icon">
                location_on
              </span>
              <span>{lead.address || 'N/A'}</span>
            </div>

            <div className="lead-digital-col">
              {lead.website ? (
                <a
                  href={lead.website.startsWith('http') ? lead.website : `https://${lead.website}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="lead-website-link"
                >
                  <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>
                    language
                  </span>
                  {lead.website.replace(/^https?:\/\/(www\.)?/, '')}
                </a>
              ) : (
                <span className="lead-website-link" style={{ cursor: 'default' }}>
                  <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>
                    link_off
                  </span>
                  No Website
                </span>
              )}
            </div>

            <div className="lead-score-col">
              <span className="lead-score-val">{lead.score || '85.0'}</span>
              <span className="lead-score-label">Signal Strength</span>
            </div>
          </div>
        ))}
      </div>

      {leads.length === 0 && (
        <div className="stream-empty-footer">
          <span>Awaiting incoming signals...</span>
        </div>
      )}
    </div>
  );
}
