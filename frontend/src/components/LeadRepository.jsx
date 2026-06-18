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
    default: return 'Google Maps'; // default
  }
};

export default function LeadRepository({ repository, onUpdateStatus }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState('score'); // score, name, sector
  const [sortOrder, setSortOrder] = useState('desc'); // desc, asc
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 6;

  // Filter leads based on search term
  const filteredLeads = repository.filter(lead => {
    const term = searchTerm.toLowerCase();
    return (
      (lead.name || '').toLowerCase().includes(term) ||
      (lead.category || '').toLowerCase().includes(term) ||
      (lead.address || '').toLowerCase().includes(term) ||
      getPlatformLabel(lead.source).toLowerCase().includes(term)
    );
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
    } else { // default: score
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

  // Reset page when search term changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm]);

  const toggleSort = (field) => {
    if (sortBy === field) {
      setSortOrder(prev => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
  };

  const downloadCSV = () => {
    if (repository.length === 0) return;
    
    // Header row
    const headers = ['Name', 'Category', 'Address', 'Phone', 'Email', 'Website', 'Source', 'Score', 'Status', 'Timestamp'];
    
    // Format each value correctly (escape quotes, handle commas)
    const formatValue = (val) => {
      if (val === null || val === undefined) return '';
      const stringVal = String(val).trim();
      // If contains comma, double quote or newline, wrap in quotes and escape internal quotes
      if (stringVal.includes(',') || stringVal.includes('"') || stringVal.includes('\n') || stringVal.includes('\r')) {
        return `"${stringVal.replace(/"/g, '""')}"`;
      }
      return stringVal;
    };

    const rows = repository.map(l => [
      l.name || '',
      l.category || '',
      l.address || '',
      l.phone || '',
      l.email || '',
      l.website || '',
      getPlatformLabel(l.source),
      l.score || '',
      l.status || 'Active',
      l.timestamp || ''
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(formatValue).join(','))
    ].join('\n');

    // Add UTF-8 BOM to make Excel open it with correct encoding
    const blob = new Blob([new Uint8Array([0xEF, 0xBB, 0xBF]), csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `leads_repository_${new Date().toISOString().split('T')[0]}.csv`);
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

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', width: '100%' }}>
      {/* Header and Controls */}
      <div className="repo-header-sec">
        <div className="repo-title-block">
          <h2>Repository</h2>
          <p>Saved Entities // {repository.length} Records</p>
        </div>

        <div className="repo-controls">
          <div className="search-filter-wrapper">
            <span className="material-symbols-outlined search-filter-icon">
              search
            </span>
            <input
              type="text"
              placeholder="Filter records..."
              className="input-filter"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <button 
            className="btn-secondary" 
            onClick={() => toggleSort('score')}
            style={{ minWidth: '80px' }}
          >
            <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>
              filter_list
            </span>
            Sort: {sortBy}
          </button>

          <button 
            className="btn-secondary" 
            onClick={downloadCSV}
            title="Download CSV"
          >
            <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>
              download
            </span>
          </button>
        </div>
      </div>

      {/* Main Table */}
      <div className="table-container">
        {/* Table Header */}
        <div className="table-hdr-grid">
          <div onClick={() => toggleSort('name')} style={{ cursor: 'pointer' }}>
            Entity Name {sortBy === 'name' && (sortOrder === 'asc' ? '▲' : '▼')}
          </div>
          <div onClick={() => toggleSort('sector')} style={{ cursor: 'pointer' }}>
            Sector {sortBy === 'sector' && (sortOrder === 'asc' ? '▲' : '▼')}
          </div>
          <div onClick={() => toggleSort('score')} style={{ cursor: 'pointer' }}>
            Intelligence Score {sortBy === 'score' && (sortOrder === 'asc' ? '▲' : '▼')}
          </div>
          <div style={{ textAlign: 'right' }}>Status</div>
        </div>

        {/* Rows */}
        <div className="table-rows-container">
          {paginatedLeads.map((lead, idx) => {
            // Score normalization for progress bar
            const rawScore = parseFloat(lead.score) || 80.0;
            const progressPercent = Math.min(Math.max((rawScore - 60) * 2.5, 10), 100); // map 60-100 to 10%-100%

            return (
              <div key={idx} className="table-row-item">
                <div className="repo-entity-col">
                  <div className="entity-avatar">
                    {getInitials(lead.name)}
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                    <span className="entity-name" style={{ fontWeight: 500 }}>{lead.name || 'Unknown Company'}</span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '2px' }}>
                      {getPlatformIcon(lead.source)}
                      <span style={{ fontSize: '16px', fontWeight: 'bold', color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
                        {getPlatformLabel(lead.source)}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="repo-sector-col">
                  <span className="sector-tag">{lead.category || 'N/A'}</span>
                </div>

                <div className="repo-score-col">
                  <div className="score-bar-bg">
                    <div
                      className="score-bar-fill"
                      style={{ width: `${progressPercent}%` }}
                    ></div>
                  </div>
                  <span className="score-num">{(rawScore / 100).toFixed(2)}</span>
                </div>

                <div className="repo-status-col" style={{ justifyContent: 'flex-end' }}>
                  <div
                    className={`status-dot ${lead.status === 'Archived' ? 'archived' : 'active'}`}
                  ></div>
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
              No saved records found in repository. Run a search to populate.
            </div>
          )}
        </div>
      </div>

      {/* Pagination Footer */}
      {sortedLeads.length > 0 && (
        <div className="pagination-footer">
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
              <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>
                chevron_left
              </span>
            </button>
            <button
              className="btn-nav-page"
              disabled={currentPage === totalPages}
              onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
              style={{ opacity: currentPage === totalPages ? 0.3 : 1 }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>
                chevron_right
              </span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
