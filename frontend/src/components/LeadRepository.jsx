import React, { useState, useEffect } from 'react';

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
      (lead.address || '').toLowerCase().includes(term)
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
    const headers = ['Name', 'Category', 'Address', 'Phone', 'Email', 'Website', 'Score', 'Status', 'Timestamp'];
    const rows = repository.map(l => [
      l.name || '',
      l.category || '',
      l.address || '',
      l.phone || '',
      l.email || '',
      l.website || '',
      l.score || '',
      l.status || 'Active',
      l.timestamp || ''
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(val => `"${String(val).replace(/"/g, '""')}"`).join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
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
                  <span className="entity-name">{lead.name || 'Unknown Company'}</span>
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
              No matching records found.
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
