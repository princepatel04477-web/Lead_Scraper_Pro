import React, { useState, useEffect } from 'react';

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
    case 'Tier A': return 'tier-exceptional';
    case 'Tier B': return 'tier-good';
    case 'Tier C': return 'tier-weak';
    case 'Tier D': return 'tier-dead';
    case 'Tier E': return 'tier-none';
    default: return 'tier-pending';
  }
};

const getTierCleanName = (tier) => {
  switch (tier) {
    case 'Tier A': return 'Exceptional';
    case 'Tier B': return 'Good';
    case 'Tier C': return 'Poor';
    case 'Tier D': return 'Dead';
    case 'Tier E': return 'No Website';
    default: return tier || 'Pending Check';
  }
};

export default function LeadRepository({ repository, onUpdateStatus }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState('score'); // score, name, sector, website_opportunity_score
  const [sortOrder, setSortOrder] = useState('desc'); // desc, asc
  const [currentPage, setCurrentPage] = useState(1);
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  
  // Advanced Filter states
  const [filterCountry, setFilterCountry] = useState('all');
  const [filterCity, setFilterCity] = useState('all');
  const [filterArea, setFilterArea] = useState('all');
  const [filterContact, setFilterContact] = useState('all'); // all, email, phone, website, no_website
  const [filterTier, setFilterTier] = useState('all'); // all, Tier A, Tier B, Tier C, Tier D, Tier E
  const [filterOpp, setFilterOpp] = useState('all'); // all, high_opp, redesign, seo, automation
  const [filterScore, setFilterScore] = useState('all'); // all, 90, 80, 70, 60, below_60
  
  // Quick Filter Chip state
  const [activeChip, setActiveChip] = useState(null);

  const itemsPerPage = 8;

  // Extract unique locations for selection dropdowns
  const uniqueCountries = [...new Set(repository.map(l => l.country).filter(Boolean))].sort();
  const uniqueCities = [...new Set(repository.map(l => l.city).filter(Boolean))].sort();
  const uniqueAreas = [...new Set(repository.map(l => l.area || l.locality).filter(Boolean))].sort();

  const handleChipClick = (chipType) => {
    setActiveChip(prev => prev === chipType ? null : chipType);
  };

  // Filter leads based on text search, advanced filters, and quick chips
  const filteredLeads = repository.filter(lead => {
    // 1. Text Search matching
    const term = searchTerm.toLowerCase();
    const matchesSearch = (
      (lead.name || '').toLowerCase().includes(term) ||
      (lead.category || '').toLowerCase().includes(term) ||
      (lead.address || '').toLowerCase().includes(term) ||
      getPlatformLabel(lead.source).toLowerCase().includes(term)
    );
    if (!matchesSearch) return false;

    // 2. Location Filters
    if (filterCountry !== 'all' && lead.country !== filterCountry) return false;
    if (filterCity !== 'all' && lead.city !== filterCity) return false;
    const leadArea = lead.area || lead.locality || '';
    if (filterArea !== 'all' && leadArea !== filterArea) return false;

    // 3. Contact Filters
    if (filterContact === 'email' && !lead.email) return false;
    if (filterContact === 'phone' && !lead.phone) return false;
    const hasWeb = lead.website && lead.website_exists !== false;
    if (filterContact === 'website' && !hasWeb) return false;
    if (filterContact === 'no_website' && hasWeb) return false;

    // 4. Website Tier Filters
    const tier = lead.website_tier || 'Pending Check';
    if (filterTier !== 'all') {
      if (filterTier === 'exceptional' && tier !== 'Tier A') return false;
      if (filterTier === 'good' && tier !== 'Tier B') return false;
      if (filterTier === 'poor' && tier !== 'Tier C') return false;
      if (filterTier === 'dead' && tier !== 'Tier D') return false;
      if (filterTier === 'none' && tier !== 'Tier E') return false;
    }

    // 5. Opportunity Filters
    const oppScore = lead.website_opportunity_score !== undefined ? lead.website_opportunity_score : (lead.website_score !== undefined ? (100 - lead.website_score) : 0);
    const checks = lead.website_checks || {};
    if (filterOpp !== 'all') {
      if (filterOpp === 'high_opp' && oppScore < 70) return false;
      if (filterOpp === 'redesign' && !["Tier C", "Tier D", "Tier E"].includes(tier)) return false;
      if (filterOpp === 'seo' && checks.seo === true) return false;
      if (filterOpp === 'automation' && checks.contact === true) return false;
    }

    // 6. Lead Quality Score Filters
    const leadScore = parseFloat(lead.score) || 0;
    if (filterScore !== 'all') {
      if (filterScore === '90' && leadScore < 90) return false;
      if (filterScore === '80' && (leadScore < 80 || leadScore >= 90)) return false;
      if (filterScore === '70' && (leadScore < 70 || leadScore >= 80)) return false;
      if (filterScore === '60' && (leadScore < 60 || leadScore >= 70)) return false;
      if (filterScore === 'below_60' && leadScore >= 60) return false;
    }

    // 7. Quick Filter Chips
    if (activeChip) {
      if (activeChip === 'no_website' && tier !== 'Tier E') return false;
      if (activeChip === 'poor_website' && tier !== 'Tier C') return false;
      if (activeChip === 'has_email' && !lead.email) return false;
      if (activeChip === 'has_phone' && !lead.phone) return false;
      if (activeChip === 'redesign_opps' && !["Tier C", "Tier D", "Tier E"].includes(tier)) return false;
      if (activeChip === 'high_value' && leadScore < 80) return false;
      if (activeChip === 'highest_opp' && oppScore < 80) return false;
      if (activeChip === 'recent') {
        const leadDate = lead.timestamp ? new Date(lead.timestamp) : new Date();
        const today = new Date();
        if (leadDate.toDateString() !== today.toDateString()) return false;
      }
    }

    return true;
  });

  // Sort leads
  const sortedLeads = [...filteredLeads].sort((a, b) => {
    let valA, valB;
    if (sortBy === 'name') {
      valA = a.name || '';
      valB = b.name || '';
    } else if (sortBy === 'sector') {
      valA = a.category || '';
      valB = b.category || '';
    } else if (sortBy === 'website_opportunity_score') {
      valA = a.website_opportunity_score !== undefined ? a.website_opportunity_score : (a.website_score !== undefined ? (100 - a.website_score) : 0);
      valB = b.website_opportunity_score !== undefined ? b.website_opportunity_score : (b.website_score !== undefined ? (100 - b.website_score) : 0);
    } else { // default: score (Lead rating)
      valA = parseFloat(a.score) || 0;
      valB = parseFloat(b.score) || 0;
    }

    if (valA < valB) return sortOrder === 'asc' ? -1 : 1;
    if (valA > valB) return sortOrder === 'asc' ? 1 : -1;
    return 0;
  });

  // Paginated leads
  const totalPages = Math.ceil(sortedLeads.length / itemsPerPage) || 1;
  const startIndex = (currentPage - 1) * itemsPerPage;
  const paginatedLeads = sortedLeads.slice(startIndex, startIndex + itemsPerPage);

  // Reset page when search/filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, filterCountry, filterCity, filterArea, filterContact, filterTier, filterOpp, filterScore, activeChip]);

  const toggleSort = (field) => {
    if (sortBy === field) {
      setSortOrder(prev => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
  };

  const clearAllFilters = () => {
    setFilterCountry('all');
    setFilterCity('all');
    setFilterArea('all');
    setFilterContact('all');
    setFilterTier('all');
    setFilterOpp('all');
    setFilterScore('all');
    setActiveChip(null);
    setSearchTerm('');
  };

  const downloadCSV = () => {
    if (repository.length === 0) return;
    
    const headers = [
      'Name', 'Category', 'Address', 'Locality', 'City', 'Country', 'Phone', 'Email', 'Website', 'Source', 
      'Lead Score', 'Website Opportunity Score', 'Website Tier', 'Website Health', 
      'Upgrade Opportunity', 'Business Maturity', 'Recommended Priority', 'Status', 'Timestamp'
    ];
    
    const formatValue = (val) => {
      if (val === null || val === undefined) return '';
      const stringVal = String(val).trim();
      if (stringVal.includes(',') || stringVal.includes('"') || stringVal.includes('\n') || stringVal.includes('\r')) {
        return `"${stringVal.replace(/"/g, '""')}"`;
      }
      return stringVal;
    };

    const rows = repository.map(l => [
      l.name || '',
      l.category || '',
      l.address || '',
      l.area || l.locality || '',
      l.city || '',
      l.country || '',
      l.phone || '',
      l.email || '',
      l.website || '',
      getPlatformLabel(l.source),
      l.score || '',
      l.website_opportunity_score !== undefined ? l.website_opportunity_score : (l.website_score !== undefined ? (100 - l.website_score) : ''),
      getTierCleanName(l.website_tier),
      l.website_health || '',
      l.upgrade_opportunity || '',
      l.business_maturity || '',
      l.recommended_priority || '',
      l.status || 'Active',
      l.timestamp || ''
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(formatValue).join(','))
    ].join('\n');

    const blob = new Blob([new Uint8Array([0xEF, 0xBB, 0xBF]), csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `leads_opportunity_repository_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const getInitials = (name) => {
    if (!name) return 'LD';
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return name.slice(0, 2).toUpperCase();
  };

  const chipStyle = (isActive) => ({
    padding: '6px 12px',
    background: isActive ? 'var(--primary-accent)' : 'var(--panel-bg)',
    border: isActive ? '1px solid var(--primary-accent)' : '1px solid var(--outline)',
    borderRadius: '20px',
    color: isActive ? '#000' : 'var(--text-muted)',
    fontSize: '11px',
    fontFamily: 'var(--font-mono)',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
    fontWeight: isActive ? 'bold' : 'normal',
    whiteSpace: 'nowrap'
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', width: '100%', gap: '8px' }}>
      {/* Header and Core Controls */}
      <div className="repo-header-sec" style={{ paddingBottom: '4px' }}>
        <div className="repo-title-block">
          <h2>Website Opportunities</h2>
          <p>Scraped Leads // {repository.length} Records</p>
        </div>

        <div className="repo-controls" style={{ flexWrap: 'wrap', gap: '8px' }}>
          <div className="search-filter-wrapper">
            <span className="material-symbols-outlined search-filter-icon">search</span>
            <input
              type="text"
              placeholder="Search leads..."
              className="input-filter"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <button 
            className="btn-secondary" 
            onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
            style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '4px',
              border: showAdvancedFilters ? '1px solid var(--primary-accent)' : '1px solid var(--outline)',
              color: showAdvancedFilters ? 'var(--primary-accent)' : 'var(--text-muted)'
            }}
          >
            <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>filter_list</span>
            Filters {showAdvancedFilters ? '▲' : '▼'}
          </button>

          <button 
            className="btn-secondary" 
            onClick={() => toggleSort('score')}
            style={{ minWidth: '80px' }}
          >
            Sort: Lead Score {sortBy === 'score' && (sortOrder === 'asc' ? '▲' : '▼')}
          </button>

          <button 
            className="btn-secondary" 
            onClick={() => toggleSort('website_opportunity_score')}
            style={{ minWidth: '80px' }}
          >
            Sort: Opportunity {sortBy === 'website_opportunity_score' && (sortOrder === 'asc' ? '▲' : '▼')}
          </button>

          <button 
            className="btn-secondary" 
            onClick={downloadCSV}
            title="Download CSV"
          >
            <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>download</span>
          </button>
        </div>
      </div>

      {/* Quick Filter Chips Row */}
      <div style={{
        display: 'flex',
        gap: '6px',
        overflowX: 'auto',
        padding: '2px 0 8px 0',
        scrollbarWidth: 'none',
        alignItems: 'center'
      }}>
        <span style={{ fontSize: '10px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap', marginRight: '4px' }}>
          QUICK FILTERS:
        </span>
        <button style={chipStyle(activeChip === 'no_website')} onClick={() => handleChipClick('no_website')}>No Website</button>
        <button style={chipStyle(activeChip === 'poor_website')} onClick={() => handleChipClick('poor_website')}>Poor Website</button>
        <button style={chipStyle(activeChip === 'has_email')} onClick={() => handleChipClick('has_email')}>Has Email</button>
        <button style={chipStyle(activeChip === 'has_phone')} onClick={() => handleChipClick('has_phone')}>Has Phone</button>
        <button style={chipStyle(activeChip === 'redesign_opps')} onClick={() => handleChipClick('redesign_opps')}>Redesign Opportunities</button>
        <button style={chipStyle(activeChip === 'high_value')} onClick={() => handleChipClick('high_value')}>High Value Prospects</button>
        <button style={chipStyle(activeChip === 'highest_opp')} onClick={() => handleChipClick('highest_opp')}>Highest Opportunity Score</button>
        <button style={chipStyle(activeChip === 'recent')} onClick={() => handleChipClick('recent')}>Recently Discovered</button>
        
        {(activeChip || filterCountry !== 'all' || filterCity !== 'all' || filterArea !== 'all' || filterContact !== 'all' || filterTier !== 'all' || filterOpp !== 'all' || filterScore !== 'all' || searchTerm) && (
          <button 
            onClick={clearAllFilters}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#EF4444',
              fontSize: '11px',
              fontFamily: 'var(--font-mono)',
              cursor: 'pointer',
              marginLeft: 'auto',
              whiteSpace: 'nowrap'
            }}
          >
            Clear All
          </button>
        )}
      </div>

      {/* Collapsible Advanced Filters Grid */}
      {showAdvancedFilters && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
          gap: '8px',
          padding: '12px',
          background: 'rgba(255, 255, 255, 0.02)',
          border: '1px solid var(--outline)',
          borderRadius: '4px',
          marginBottom: '8px'
        }}>
          {/* Location filters */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <span style={{ fontSize: '9px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>COUNTRY</span>
            <select className="settings-select" value={filterCountry} onChange={(e) => setFilterCountry(e.target.value)} style={{ width: '100%' }}>
              <option value="all">All Countries</option>
              {uniqueCountries.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <span style={{ fontSize: '9px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>CITY</span>
            <select className="settings-select" value={filterCity} onChange={(e) => setFilterCity(e.target.value)} style={{ width: '100%' }}>
              <option value="all">All Cities</option>
              {uniqueCities.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <span style={{ fontSize: '9px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>AREA / LOCALITY</span>
            <select className="settings-select" value={filterArea} onChange={(e) => setFilterArea(e.target.value)} style={{ width: '100%' }}>
              <option value="all">All Areas</option>
              {uniqueAreas.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>

          {/* Contact filter */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <span style={{ fontSize: '9px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>CONTACTS</span>
            <select className="settings-select" value={filterContact} onChange={(e) => setFilterContact(e.target.value)} style={{ width: '100%' }}>
              <option value="all">All Contact States</option>
              <option value="email">Has Email</option>
              <option value="phone">Has Phone</option>
              <option value="website">Has Website</option>
              <option value="no_website">No Website</option>
            </select>
          </div>

          {/* Website Quality Tier */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <span style={{ fontSize: '9px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>WEBSITE QUALITY</span>
            <select className="settings-select" value={filterTier} onChange={(e) => setFilterTier(e.target.value)} style={{ width: '100%' }}>
              <option value="all">All Web Tiers</option>
              <option value="exceptional">Tier A: Exceptional</option>
              <option value="good">Tier B: Good</option>
              <option value="poor">Tier C: Poor</option>
              <option value="dead">Tier D: Dead</option>
              <option value="none">Tier E: No Website</option>
            </select>
          </div>

          {/* Opportunity Filters */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <span style={{ fontSize: '9px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>OPPORTUNITY TYPES</span>
            <select className="settings-select" value={filterOpp} onChange={(e) => setFilterOpp(e.target.value)} style={{ width: '100%' }}>
              <option value="all">All Opportunities</option>
              <option value="high_opp">High Opportunity (70+)</option>
              <option value="redesign">Needs Redesign (C/D/E)</option>
              <option value="seo">SEO Services Candidate</option>
              <option value="automation">Needs Automation/Form</option>
            </select>
          </div>

          {/* Lead Quality Score range */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <span style={{ fontSize: '9px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>LEAD RATING SCORE</span>
            <select className="settings-select" value={filterScore} onChange={(e) => setFilterScore(e.target.value)} style={{ width: '100%' }}>
              <option value="all">All Scores</option>
              <option value="90">90+ Excellent</option>
              <option value="80">80+ Strong</option>
              <option value="70">70+ Moderate</option>
              <option value="60">60+ Base</option>
              <option value="below_60">Below 60</option>
            </select>
          </div>
        </div>
      )}

      {/* Main Table */}
      <div className="table-container">
        {/* Table Header */}
        <div className="table-hdr-grid" style={{ gridTemplateColumns: '2.5fr 1.2fr 1.2fr 1.5fr 1fr' }}>
          <div onClick={() => toggleSort('name')} style={{ cursor: 'pointer' }}>
            Entity Name {sortBy === 'name' && (sortOrder === 'asc' ? '▲' : '▼')}
          </div>
          <div onClick={() => toggleSort('sector')} style={{ cursor: 'pointer' }}>
            Sector {sortBy === 'sector' && (sortOrder === 'asc' ? '▲' : '▼')}
          </div>
          <div>Lead Rating</div>
          <div>Opportunity Score</div>
          <div style={{ textAlign: 'right' }}>Status</div>
        </div>

        {/* Rows */}
        <div className="table-rows-container">
          {paginatedLeads.map((lead, idx) => {
            const leadScore = parseFloat(lead.score) || 80.0;
            const scorePercent = Math.min(Math.max((leadScore - 20) * 1.25, 10), 100);
            
            const oppScore = lead.website_opportunity_score !== undefined ? lead.website_opportunity_score : (lead.website_score !== undefined ? (100 - lead.website_score) : 0);
            const tier = lead.website_tier || 'Pending Check';
            const cleanTier = getTierCleanName(tier);

            return (
              <div key={idx} className="table-row-item" style={{ gridTemplateColumns: '2.5fr 1.2fr 1.2fr 1.5fr 1fr', padding: '12px 16px' }}>
                <div className="repo-entity-col">
                  <div className="entity-avatar">
                    {getInitials(lead.name)}
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                    <span className="entity-name" style={{ fontWeight: 500 }}>{lead.name || 'Unknown Company'}</span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '2px', flexWrap: 'wrap' }}>
                      {getPlatformIcon(lead.source)}
                      <span style={{ fontSize: '10px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                        {getPlatformLabel(lead.source)}
                      </span>
                      {lead.area && (
                        <span style={{ fontSize: '10px', color: 'var(--primary-accent)', fontFamily: 'var(--font-mono)' }}>
                          • {lead.area}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="repo-sector-col">
                  <span className="sector-tag">{lead.category || 'N/A'}</span>
                </div>

                <div className="repo-score-col" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: '4px' }}>
                  <div className="score-bar-bg" style={{ width: '80px' }}>
                    <div
                      className="score-bar-fill"
                      style={{ width: `${scorePercent}%`, background: 'var(--primary-accent)' }}
                    ></div>
                  </div>
                  <span className="score-num" style={{ fontSize: '11px', fontFamily: 'var(--font-mono)' }}>
                    Rating: {leadScore.toFixed(0)}/100
                  </span>
                </div>

                <div className="repo-web-col" style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <span className={`tier-badge ${getTierColorClass(tier)}`} style={{ padding: '2px 6px', fontSize: '9px', width: 'fit-content' }}>
                    {cleanTier}
                  </span>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    Opportunity: {oppScore}/100
                  </span>
                </div>

                <div className="repo-status-col" style={{ justifyContent: 'flex-end' }}>
                  <div className={`status-dot ${lead.status === 'Archived' ? 'archived' : 'active'}`}></div>
                  <select
                    value={lead.status || 'Active'}
                    onChange={(e) => onUpdateStatus(lead.name, e.target.value)}
                    className="status-select"
                    style={{
                      color: lead.status === 'Archived' ? 'var(--text-dim)' : 'var(--text-muted)'
                    }}
                  >
                    <option value="Active">Active</option>
                    <option value="Archived">Archived</option>
                  </select>
                </div>
              </div>
            );
          })}

          {sortedLeads.length === 0 && (
            <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              No opportunity leads matching the active filters.
            </div>
          )}
        </div>
      </div>

      {/* Pagination Footer */}
      {sortedLeads.length > 0 && (
        <div className="pagination-footer" style={{ marginTop: 'auto', paddingTop: '8px' }}>
          <span className="pagination-info">
            Showing {startIndex + 1}-{Math.min(startIndex + itemsPerPage, sortedLeads.length)} of {sortedLeads.length}
          </span>
          <div className="pagination-buttons">
            <button
              className="btn-nav-page"
              disabled={currentPage === 1}
              onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
              style={{ opacity: currentPage === 1 ? 0.3 : 1 }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>chevron_left</span>
            </button>
            <button
              className="btn-nav-page"
              disabled={currentPage === totalPages}
              onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
              style={{ opacity: currentPage === totalPages ? 0.3 : 1 }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>chevron_right</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
