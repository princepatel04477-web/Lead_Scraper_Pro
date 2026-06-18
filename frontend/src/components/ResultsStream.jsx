import React from 'react';

const getPlatformIcon = (source) => {
  switch (source) {
    case 'google_maps':
      return (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--primary-accent)" strokeWidth="2.5" style={{ minWidth: '18px' }}>
          <path d="M12 2a8 8 0 0 0-8 8c0 1.89.62 3.63 1.66 5.04L12 22l6.34-6.96A7.975 7.975 0 0 0 20 10a8 8 0 0 0-8-8z"/>
          <circle cx="12" cy="10" r="3" fill="var(--primary-accent)"/>
        </svg>
      );
    case 'yellowpages':
      return (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#FBBF24" strokeWidth="2.5" style={{ minWidth: '18px' }}>
          <rect x="3" y="3" width="18" height="18" rx="2" fill="rgba(251, 191, 36, 0.1)"/>
          <line x1="9" y1="3" x2="9" y2="21"/>
        </svg>
      );
    case 'instagram':
      return (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#EC4899" strokeWidth="2.5" style={{ minWidth: '18px' }}>
          <rect x="2" y="2" width="20" height="20" rx="5" ry="5"/>
          <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/>
          <line x1="17.5" y1="6.5" x2="17.51" y2="6.5"/>
        </svg>
      );
    case 'facebook':
      return (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#3B82F6" strokeWidth="2.5" style={{ minWidth: '18px' }}>
          <path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z" fill="rgba(59, 130, 246, 0.1)"/>
        </svg>
      );
    default:
      return (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="2.5" style={{ minWidth: '18px' }}>
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="12"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
      );
  }
};

const getPlatformLabel = (source) => {
  switch (source) {
    case 'google_maps': return 'Google Maps';
    case 'yellowpages': return 'Yellow Pages';
    case 'instagram': return 'Instagram';
    case 'facebook': return 'Facebook';
    default: return 'Google Maps';
  }
};

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
              <span className="lead-name" style={{ fontWeight: 500 }}>{lead.name || 'Unknown Company'}</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '2px' }}>
                {getPlatformIcon(lead.source)}
                <span style={{ fontSize: '16px', fontWeight: 'bold', color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
                  {getPlatformLabel(lead.source)}
                </span>
              </div>
              <span className="lead-sector" style={{ marginTop: '4px' }}>{lead.category || 'N/A'}</span>
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
