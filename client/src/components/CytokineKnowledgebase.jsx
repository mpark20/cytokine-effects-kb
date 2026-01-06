import React, { useState, useEffect } from 'react';
import { Search, Filter, Download, ChevronLeft, ChevronRight, X, Settings } from 'lucide-react';

const API_BASE_URL = 'http://localhost:8000';

const CytokineKnowledgebase = () => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({ page: 1, limit: 50, total: 0, total_pages: 0 });
  const [filters, setFilters] = useState({});
  const [searchTerm, setSearchTerm] = useState('');
  const [stats, setStats] = useState(null);
  
  // Available filter columns
  const [filterOptions, setFilterOptions] = useState({});
  const [showFilters, setShowFilters] = useState(false);
  const [showColumnSelector, setShowColumnSelector] = useState(false);
  
  // Column visibility
  const defaultVisibleColumns = ['cytokine_name', 'cell_type', 'species', 'causality_type', 'cytokine_effect', 'regulated_genes', 'chunk_id', 'key_sentences', 'citation_id'];
  const [visibleColumns, setVisibleColumns] = useState(defaultVisibleColumns);
  
  const allColumns = [
    "cytokine_name",
    "cell_type",
    "cytokine_effect",
    "causality_type",
    "species",
    "chunk_id",
    "key_sentences",
    "citation_id"
];

  const filterableColumns = [
    { key: 'cytokine_name', label: 'Cytokine Name' },
    { key: 'cell_type', label: 'Cell Type' },
    { key: 'species', label: 'Species' },
    { key: 'causality_type', label: 'Causality Type' },
    { key: 'experimental_system_type', label: 'Experimental System' },
    { key: 'publication_type', label: 'Publication Type' }
  ];

  // Fetch data
  const fetchData = async (page = 1) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        limit: pagination.limit.toString(),
        fields: visibleColumns.join(',')
      });
      
      if (searchTerm) params.append('search', searchTerm);
      Object.keys(filters).forEach(key => {
        if (filters[key]) params.append(key, filters[key]);
      });

      const response = await fetch(`${API_BASE_URL}/api/interactions?${params}`);
      const result = await response.json();
      
      setData(result.data);
      setPagination(result.pagination);
    } catch (error) {
      console.error('Error fetching data:', error);
      alert('Error loading data. Make sure the backend server is running.');
    } finally {
      setLoading(false);
    }
  };

  // Fetch stats
  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/stats`);
      const result = await response.json();
      setStats(result);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  // Fetch filter options for a column
  const fetchFilterOptions = async (column) => {
    if (filterOptions[column]) return;
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/filters/${column}`);
      const result = await response.json();
      setFilterOptions(prev => ({ ...prev, [column]: result.values }));
    } catch (error) {
      console.error(`Error fetching filter options for ${column}:`, error);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  useEffect(() => {
    fetchData(1);
  }, [filters, searchTerm, visibleColumns]);

  const handleFilterChange = (column, value) => {
    setFilters(prev => ({ ...prev, [column]: value }));
  };

  const clearFilter = (column) => {
    const newFilters = { ...filters };
    delete newFilters[column];
    setFilters(newFilters);
  };

  const clearAllFilters = () => {
    setFilters({});
    setSearchTerm('');
  };

  const toggleColumn = (column) => {
    setVisibleColumns(prev => 
      prev.includes(column) 
        ? prev.filter(c => c !== column)
        : [...prev, column]
    );
  };

  const exportToCSV = () => {
    if (data.length === 0) return;
    
    const headers = visibleColumns.join(',');
    const rows = data.map(row => 
      visibleColumns.map(col => {
        const val = row[col] || '';
        return `"${String(val).replace(/"/g, '""')}"`;
      }).join(',')
    );
    
    const csv = [headers, ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `cytokine_data_page_${pagination.page}.csv`;
    a.click();
  };

  const formatColumnName = (col) => {
    return col.split('_').map(word => 
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
  };

  const truncateText = (text, maxLength = 100) => {
    if (!text) return '-';
    const str = String(text);
    return str.length > maxLength ? str.substring(0, maxLength) + '...' : str;
  };

  return (
    <div>
      {/* Header */}
      <div className="container">
        <div className="px-6 py-8">
          <h1 className="text-4xl font-bold mb-2">Cytokine Interactions Knowledgebase</h1>
          <p className="text-gray-400">Explore cytokine-cell interactions from PMC literature</p>
          
          {stats && (
            <div className="grid grid-cols-4 gap-4 mt-6">
              <div className="bg-white/10 rounded-lg p-4 backdrop-blur">
                <div className="text-2xl font-bold">{stats.total_interactions?.toLocaleString()}</div>
                <div className="text-sm text-gray-400">Total Interactions</div>
              </div>
              <div className="bg-white/10 rounded-lg p-4 backdrop-blur">
                <div className="text-2xl font-bold">{stats.unique_cytokines?.toLocaleString()}</div>
                <div className="text-sm text-gray-400">Unique Cytokines</div>
              </div>
              <div className="bg-white/10 rounded-lg p-4 backdrop-blur">
                <div className="text-2xl font-bold">{stats.unique_cell_types?.toLocaleString()}</div>
                <div className="text-sm text-gray-400">Cell Types</div>
              </div>
              <div className="bg-white/10 rounded-lg p-4 backdrop-blur">
                <div className="text-2xl font-bold">{stats.unique_species?.toLocaleString()}</div>
                <div className="text-sm text-gray-400">Species</div>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="px-6 py-6">
        {/* Search and Controls */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <div className="mb-4 space-y-4">
            {/* Search bar */}
            <div className="relative">
              <Search className="absolute left-3 top-3 text-gray-400" size={20} />
              <input
                type="text"
                placeholder="Search cytokines, genes, pathways, cell types..."
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>

            {/* Buttons */}
            <div className="flex flex-wrap gap-3">
              <button
                onClick={() => setShowFilters(!showFilters)}
                className="px-6 py-2 bg-green-600 text-gray rounded-lg hover:bg-gray-700 flex items-center gap-2"
              >
                <Filter size={20} />
                Filters {Object.keys(filters).length > 0 && `(${Object.keys(filters).length})`}
              </button>

              <button
                onClick={() => setShowColumnSelector(!showColumnSelector)}
                className="px-6 py-2 bg-gray-600 text-gray rounded-lg hover:bg-gray-700 flex items-center gap-2"
              >
                <Settings size={20} />
                Columns
              </button>

              <button
                onClick={exportToCSV}
                className="px-6 py-2 bg-green-600 rounded-lg hover:bg-gray-700 flex items-center gap-2"
                disabled={data.length === 0}
              >
                <Download size={20} />
                Export
              </button>
            </div>
          </div>

          {/* Active Filters */}
          {Object.keys(filters).length > 0 && (
            <div className="flex flex-wrap gap-2 mt-4">
              {Object.entries(filters).map(([key, value]) => (
                <span key={key} className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm flex items-center gap-2">
                  {formatColumnName(key)}: {value}
                  <button onClick={() => clearFilter(key)} className="hover:text-blue-600">
                    <X size={14} />
                  </button>
                </span>
              ))}
              <button
                onClick={clearAllFilters}
                className="text-sm text-red-600 hover:text-red-700 font-medium"
              >
                Clear All
              </button>
            </div>
          )}

          {/* Filter Panel */}
          {showFilters && (
            <div className="mt-4 grid grid-cols-3 gap-4 p-4 bg-gray-50 rounded-lg">
              {filterableColumns.map(({ key, label }) => (
                <div key={key}>
                  <label className="block text-sm font-medium text-gray-700 mb-2">{label}</label>
                  <input
                    type="text"
                    placeholder={`Filter by ${label.toLowerCase()}...`}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    value={filters[key] || ''}
                    onChange={(e) => handleFilterChange(key, e.target.value)}
                    onFocus={() => fetchFilterOptions(key)}
                  />
                </div>
              ))}
            </div>
          )}

          {/* Column Selector */}
          {showColumnSelector && (
            <div className="mt-4 p-4 bg-gray-50 rounded-lg">
              <h3 className="font-semibold mb-3">Select Visible Columns</h3>
              <div className="grid grid-cols-4 gap-2">
                {allColumns.map(col => (
                  <label key={col} className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={visibleColumns.includes(col)}
                      onChange={() => toggleColumn(col)}
                      className="rounded text-blue-600 focus:ring-blue-500"
                    />
                    {formatColumnName(col)}
                  </label>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Data Table */}
        <div className="bg-white rounded-lg shadow-md overflow-hidden">
          {loading ? (
            <div className="p-12 text-center">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
              <p className="mt-4 text-gray-600">Loading data...</p>
            </div>
          ) : (
            <>
              <div className="w-full overflow-x-auto">
                <table className="w-full table-fixed">
                  <thead className="bg-gray-100 border-b border-gray-200">
                    <tr>
                      {visibleColumns.map(col => (
                        <th key={col} className="px-4 py-3 text-left text-sm font-semibold text-gray-700 break-words">
                          {formatColumnName(col)}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {data.map((row, idx) => (
                      <tr key={row.id || idx} className="hover:bg-gray-50">
                        {visibleColumns.map(col => (
                          <td key={col} className="px-4 py-3 text-sm text-gray-800 break-words whitespace-normal">
                            {truncateText(row[col])}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex items-center justify-between">
                <div className="text-sm text-gray-600">
                  Showing {((pagination.page - 1) * pagination.limit) + 1} to{' '}
                  {Math.min(pagination.page * pagination.limit, pagination.total)} of{' '}
                  {pagination.total?.toLocaleString()} results
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => fetchData(pagination.page - 1)}
                    disabled={pagination.page === 1}
                    className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                  >
                    <ChevronLeft size={16} />
                    Previous
                  </button>
                  <span className="px-4 py-2 text-sm text-gray-600">
                    Page {pagination.page} of {pagination.total_pages}
                  </span>
                  <button
                    onClick={() => fetchData(pagination.page + 1)}
                    disabled={pagination.page === pagination.total_pages}
                    className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                  >
                    Next
                    <ChevronRight size={16} />
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default CytokineKnowledgebase;