import React, { useState } from 'react';

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

const getTierColorClass = (tier) => {
  switch (tier) {
    case 'Exceptional Website': return 'tier-exceptional';
    case 'Good Website': return 'tier-good';
    case 'Weak Website': return 'tier-weak';
    case 'Dead Website': return 'tier-dead';
    case 'No Website': return 'tier-none';
    default: return 'tier-pending';
  }
};

export default function ResultsStream({ leads, state }) {
  const [expandedLead, setExpandedLead] = useState(null);

  const toggleExpand = (leadName) => {
    if (expandedLead === leadName) {
      setExpandedLead(null);
    } else {
      setExpandedLead(leadName);
    }
  };

  const getOpportunityBadge = (opp) => {
    if (opp === 'High') {
      return <span className="opp-tag high-opp">🔥 High Upgrade Opportunity</span>;
    }
    if (opp === 'High Value Client') {
      return <span className="opp-tag high-value-opp">💎 High Value Client</span>;
    }
    if (opp === 'Medium') {
      return <span className="opp-tag med-opp">⚡ Medium Opportunity</span>;
    }
    return <span className="opp-tag low-opp">🛡️ Low Opportunity</span>;
  };

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
        <div>Website Status</div>
        <div style={{ textAlign: 'right' }}>Score</div>
      </div>

      {/* Stream Container */}
      <div className="lead-stream-container">
        {leads.map((lead, idx) => {
          const isExpanded = expandedLead === lead.name;
          const tier = lead.website_tier || 'Pending Check';
          
          return (
            <div key={idx} className={`lead-row-card-wrapper ${isExpanded ? 'expanded' : ''}`}>
              <div className="lead-row-card" onClick={() => toggleExpand(lead.name)} style={{ cursor: 'pointer' }}>
                <div className="lead-name-col">
                  <span className="lead-name" style={{ fontWeight: 500 }}>{lead.name || 'Unknown Company'}</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '2px' }}>
                    {getPlatformIcon(lead.source)}
                    <span style={{ fontSize: '14px', fontWeight: 'bold', color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
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
                  <span className={`tier-badge ${getTierColorClass(tier)}`}>
                    {tier}
                  </span>
                  {lead.website ? (
                    <a
                      href={lead.website.startsWith('http') ? lead.website : `https://${lead.website}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="lead-website-link"
                      onClick={(e) => e.stopPropagation()}
                      style={{ marginTop: '4px', display: 'flex' }}
                    >
                      <span className="material-symbols-outlined" style={{ fontSize: '14px', marginRight: '4px' }}>
                        link
                      </span>
                      {lead.website.replace(/^https?:\/\/(www\.)?/, '')}
                    </a>
                  ) : (
                    <span style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '2px', fontFamily: 'var(--font-mono)' }}>
                      No Domain Listed
                    </span>
                  )}
                </div>

                <div className="lead-score-col">
                  <span className="lead-score-val">{lead.score || '85.0'}</span>
                  <span className="lead-score-label">Lead Rating</span>
                </div>
              </div>

              {/* Expandable Audit Panel */}
              {isExpanded && (
                <div className="lead-audit-panel">
                  <div className="audit-panel-grid">
                    {/* Left side: Opportunity and scoring */}
                    <div className="audit-left-block">
                      <div className="audit-header-title">Website Quality Audit</div>
                      
                      <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', margin: '8px 0' }}>
                        <span className="audit-score-giant">{lead.website_score || 0}</span>
                        <span className="audit-score-max">/100</span>
                      </div>
                      
                      <div className="score-bar-bg" style={{ height: '6px', borderRadius: '3px', margin: '4px 0 12px 0' }}>
                        <div
                          className="score-bar-fill"
                          style={{
                            width: `${lead.website_score || 0}%`,
                            background: lead.website_score >= 80 ? '#10B981' : lead.website_score >= 50 ? '#14B8A6' : lead.website_score >= 20 ? '#F59E0B' : '#EF4444'
                          }}
                        ></div>
                      </div>

                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        <div>
                          <div className="audit-meta-label">Health & Status</div>
                          <span className="audit-meta-val" style={{ textTransform: 'capitalize' }}>
                            {lead.website_health || 'Offline'} ({lead.website_exists ? 'Online' : 'Offline'})
                          </span>
                        </div>
                        
                        <div>
                          <div className="audit-meta-label">Opportunity Rating</div>
                          <div style={{ marginTop: '2px' }}>
                            {getOpportunityBadge(lead.upgrade_opportunity)}
                          </div>
                        </div>

                        <div>
                          <div className="audit-meta-label">Business Maturity</div>
                          <span className="audit-meta-val" style={{ color: 'var(--text-primary)' }}>
                            {lead.business_maturity || 'Struggling'}
                          </span>
                        </div>

                        <div>
                          <div className="audit-meta-label">Target Priority</div>
                          <span className={`priority-tag ${lead.recommended_priority ? lead.recommended_priority.toLowerCase() : 'low'}`}>
                            {lead.recommended_priority || 'Low'} Priority
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Right side: Detailed Checks */}
                    <div className="audit-right-block">
                      <div className="audit-header-title">Technical Check List</div>
                      
                      {lead.website_exists ? (
                        <div className="technical-checks-grid">
                          <div className={`check-item ${lead.website_checks?.ssl ? 'pass' : 'fail'}`}>
                            <span className="material-symbols-outlined check-icon">
                              {lead.website_checks?.ssl ? 'check_circle' : 'cancel'}
                            </span>
                            <span>SSL Certificate</span>
                          </div>
                          
                          <div className={`check-item ${lead.website_checks?.responsive ? 'pass' : 'fail'}`}>
                            <span className="material-symbols-outlined check-icon">
                              {lead.website_checks?.responsive ? 'check_circle' : 'cancel'}
                            </span>
                            <span>Mobile Optimization</span>
                          </div>

                          <div className={`check-item ${lead.website_checks?.speed ? 'pass' : 'fail'}`}>
                            <span className="material-symbols-outlined check-icon">
                              {lead.website_checks?.speed ? 'check_circle' : 'cancel'}
                            </span>
                            <span>Page Speed Status</span>
                          </div>

                          <div className={`check-item ${lead.website_checks?.contact ? 'pass' : 'fail'}`}>
                            <span className="material-symbols-outlined check-icon">
                              {lead.website_checks?.contact ? 'check_circle' : 'cancel'}
                            </span>
                            <span>Contact Page Link</span>
                          </div>

                          <div className={`check-item ${lead.website_checks?.about ? 'pass' : 'fail'}`}>
                            <span className="material-symbols-outlined check-icon">
                              {lead.website_checks?.about ? 'check_circle' : 'cancel'}
                            </span>
                            <span>About Page Link</span>
                          </div>

                          <div className={`check-item ${lead.website_checks?.services ? 'pass' : 'fail'}`}>
                            <span className="material-symbols-outlined check-icon">
                              {lead.website_checks?.services ? 'check_circle' : 'cancel'}
                            </span>
                            <span>Service Pages Link</span>
                          </div>

                          <div className={`check-item ${lead.website_checks?.team ? 'pass' : 'fail'}`}>
                            <span className="material-symbols-outlined check-icon">
                              {lead.website_checks?.team ? 'check_circle' : 'cancel'}
                            </span>
                            <span>Team/Staff Page</span>
                          </div>

                          <div className={`check-item ${lead.website_checks?.portfolio ? 'pass' : 'fail'}`}>
                            <span className="material-symbols-outlined check-icon">
                              {lead.website_checks?.portfolio ? 'check_circle' : 'cancel'}
                            </span>
                            <span>Portfolio/Showcase</span>
                          </div>

                          <div className={`check-item ${lead.website_checks?.testimonials ? 'pass' : 'fail'}`}>
                            <span className="material-symbols-outlined check-icon">
                              {lead.website_checks?.testimonials ? 'check_circle' : 'cancel'}
                            </span>
                            <span>Testimonials Page</span>
                          </div>

                          <div className={`check-item ${lead.website_checks?.careers ? 'pass' : 'fail'}`}>
                            <span className="material-symbols-outlined check-icon">
                              {lead.website_checks?.careers ? 'check_circle' : 'cancel'}
                            </span>
                            <span>Careers/Jobs Page</span>
                          </div>

                          <div className={`check-item ${lead.website_checks?.blog ? 'pass' : 'fail'}`}>
                            <span className="material-symbols-outlined check-icon">
                              {lead.website_checks?.blog ? 'check_circle' : 'cancel'}
                            </span>
                            <span>Blog/Insights Page</span>
                          </div>

                          <div className={`check-item ${lead.website_checks?.multiple_contacts ? 'pass' : 'fail'}`}>
                            <span className="material-symbols-outlined check-icon">
                              {lead.website_checks?.multiple_contacts ? 'check_circle' : 'cancel'}
                            </span>
                            <span>Multiple Contacts</span>
                          </div>
                        </div>
                      ) : (
                        <div className="no-website-audit-box">
                          <span className="material-symbols-outlined" style={{ fontSize: '48px', color: 'var(--text-dim)' }}>
                            link_off
                          </span>
                          <span style={{ fontSize: '13px', marginTop: '8px', color: 'var(--text-muted)' }}>
                            Detailed technical checklist is unavailable because the company has no active standalone website.
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {leads.length === 0 && (
        <div className="stream-empty-footer">
          <span>Awaiting incoming signals...</span>
        </div>
      )}
    </div>
  );
}
