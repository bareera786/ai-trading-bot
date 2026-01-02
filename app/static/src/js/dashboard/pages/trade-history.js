import { fetchJson } from '../utils/network.js';

let currentPage = 1;
let currentFilters = {
  symbol: '',
  days: '',
  type: 'all'
};
let totalPages = 1;
let availableSymbols = new Set();

export async function loadTradeHistory() {
  try {
    const user = await fetchJson('/api/current_user');
    const isAdmin = Boolean(user?.is_admin);
    const userId = user?.id;

    // Build query parameters
    const params = new URLSearchParams({
      mode: 'ultimate',
      page: currentPage,
      merge_db: isAdmin ? '1' : '0'
    });

    if (currentFilters.symbol) params.append('symbol', currentFilters.symbol);
    if (currentFilters.days) params.append('days', currentFilters.days);

    // Add execution mode filter based on type
    if (currentFilters.type === 'futures') {
      params.append('execution_mode', 'futures');
    } else if (currentFilters.type === 'spot') {
      params.append('execution_mode', 'real');
    }

    const endpoint = isAdmin
      ? `/api/trades?${params.toString()}`
      : `/api/user/${userId}/trades?${params.toString()}`;

    const data = await fetchJson(endpoint);

    if (!data || data.error || !Array.isArray(data.trades)) {
      console.error('Failed to load trade history:', data?.error || 'Invalid response');
      renderEmptyState('Unable to load trade history');
      return;
    }

    // Update pagination info
    totalPages = data.total_pages || 1;
    updatePaginationControls(data.current_page, totalPages);

    // Collect available symbols for filter
    data.trades.forEach(trade => {
      if (trade.symbol) availableSymbols.add(trade.symbol);
    });
    updateSymbolFilter();

    populateTradeHistoryTable(data.trades);
  } catch (error) {
    console.error('Error loading trade history:', error);
    renderEmptyState('Unable to load trade history');
  }
}

function populateTradeHistoryTable(trades) {
  const tbody = document.getElementById('trade-history-table');
  if (!tbody) return;

  tbody.innerHTML = '';

  if (trades.length === 0) {
    const row = document.createElement('tr');
    row.innerHTML = '<td colspan="9" style="text-align: center; padding: 2rem;">No trades found</td>';
    tbody.appendChild(row);
    return;
  }

  trades.forEach((trade) => {
    const row = document.createElement('tr');

    // Format timestamp - API returns ISO string
    const timestamp = new Date(trade.timestamp);
    const dateString = timestamp.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });

    // Format P&L with color
    const pnl = Number(trade.pnl) || 0;
    const pnlClass = pnl >= 0 ? 'text-success' : 'text-danger';
    const pnlText = pnl >= 0 ? `+$${pnl.toFixed(4)}` : `-$${Math.abs(pnl).toFixed(4)}`;

    const quantity = Number(trade.quantity || trade.qty) || 0;
    const entryPrice = Number(trade.entry_price ?? trade.price ?? trade.fill_price) || 0;
    const status = trade.status || trade.state || 'unknown';
    const side = trade.side || trade.position_side || 'N/A';
    const symbol = trade.symbol || trade.ticker || 'N/A';

    // Determine trade type
    const tradeType = trade.execution_mode === 'futures' ? 'Futures' :
                     trade.execution_mode === 'real' ? 'Spot' : 'Paper';

    // Leverage (only for futures)
    const leverage = trade.leverage ? `${trade.leverage}x` : '-';

    row.innerHTML = `
      <td>${dateString}</td>
      <td>${symbol}</td>
      <td><span class="trade-type-${tradeType.toLowerCase()}">${tradeType}</span></td>
      <td>${side}</td>
      <td>${quantity.toFixed(4)}</td>
      <td>$${entryPrice.toFixed(4)}</td>
      <td>${leverage}</td>
      <td class="${pnlClass}">${pnlText}</td>
      <td><span class="status-indicator status-${getStatusClass(status)}">${status}</span></td>
    `;

    // Attach click handler to open detail view
    row.style.cursor = 'pointer';
    row.addEventListener('click', () => {
      showTradeDetail(trade);
    });

    tbody.appendChild(row);
  });
}

function showTradeDetail(trade) {
  // Ensure modal exists in DOM
  const modal = document.getElementById('trade-detail-modal');
  if (!modal) {
    // Fallback alert if modal markup isn't present
    alert('Trade details:\n' + JSON.stringify(trade, null, 2));
    return;
  }

  modal.querySelector('.trade-detail-timestamp')?.textContent = new Date(trade.timestamp).toLocaleString();
  modal.querySelector('.trade-detail-symbol')?.textContent = trade.symbol || trade.ticker || 'N/A';
  modal.querySelector('.trade-detail-side')?.textContent = trade.side || trade.position_side || 'N/A';
  modal.querySelector('.trade-detail-qty')?.textContent = Number(trade.quantity || trade.qty || 0).toFixed(8);
  modal.querySelector('.trade-detail-entry')?.textContent = Number(trade.entry_price ?? trade.price ?? trade.fill_price || 0).toFixed(8);
  modal.querySelector('.trade-detail-exit')?.textContent = Number(trade.exit_price || trade.close_price || 0).toFixed(8);
  modal.querySelector('.trade-detail-pnl')?.textContent = (Number(trade.pnl) || 0).toFixed(8);
  modal.querySelector('.trade-detail-status')?.textContent = trade.status || trade.state || 'N/A';
  modal.querySelector('.trade-detail-meta')?.textContent = JSON.stringify(trade, null, 2);

  modal.style.display = 'flex';
}

function renderEmptyState(message) {
  const tbody = document.getElementById('trade-history-table');
  if (!tbody) return;
  tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; padding: 2rem;">${message}</td></tr>`;
}

function getStatusClass(status) {
  switch (status?.toLowerCase()) {
    case 'filled':
    case 'closed':
    case 'success':
      return 'success';
    case 'failed':
      return 'error';
    default:
      return 'warning';
  }
}

function updatePaginationControls(currentPage, totalPages) {
  const paginationDiv = document.getElementById('trade-pagination');
  const pageInfo = document.getElementById('page-info');
  const prevBtn = document.getElementById('prev-page-btn');
  const nextBtn = document.getElementById('next-page-btn');

  if (!paginationDiv || !pageInfo || !prevBtn || !nextBtn) return;

  if (totalPages > 1) {
    paginationDiv.style.display = 'block';
    pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
    prevBtn.disabled = currentPage <= 1;
    nextBtn.disabled = currentPage >= totalPages;
  } else {
    paginationDiv.style.display = 'none';
  }
}

function updateSymbolFilter() {
  const symbolSelect = document.getElementById('trade-symbol-filter');
  if (!symbolSelect) return;

  // Clear existing options except "All Symbols"
  while (symbolSelect.options.length > 1) {
    symbolSelect.remove(1);
  }

  // Add available symbols
  Array.from(availableSymbols).sort().forEach(symbol => {
    const option = document.createElement('option');
    option.value = symbol;
    option.textContent = symbol;
    symbolSelect.appendChild(option);
  });
}

function setupFilters() {
  const filterSelect = document.getElementById('trade-filter-select');
  const symbolSelect = document.getElementById('trade-symbol-filter');
  const daysSelect = document.getElementById('trade-days-filter');
  const refreshBtn = document.getElementById('refresh-trades-btn');
  const prevBtn = document.getElementById('prev-page-btn');
  const nextBtn = document.getElementById('next-page-btn');

  if (filterSelect) {
    filterSelect.addEventListener('change', (e) => {
      currentFilters.type = e.target.value;
      currentPage = 1;
      loadTradeHistory();
    });
  }

  if (symbolSelect) {
    symbolSelect.addEventListener('change', (e) => {
      currentFilters.symbol = e.target.value;
      currentPage = 1;
      loadTradeHistory();
    });
  }

  if (daysSelect) {
    daysSelect.addEventListener('change', (e) => {
      currentFilters.days = e.target.value;
      currentPage = 1;
      loadTradeHistory();
    });
  }

  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      currentPage = 1;
      loadTradeHistory();
    });
  }

  if (prevBtn) {
    prevBtn.addEventListener('click', () => {
      if (currentPage > 1) {
        currentPage--;
        loadTradeHistory();
      }
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener('click', () => {
      if (currentPage < totalPages) {
        currentPage++;
        loadTradeHistory();
      }
    });
  }
}

async function exportTradesToCSV() {
  try {
    const user = await fetchJson('/api/current_user');
    const isAdmin = Boolean(user?.is_admin);
    const userId = user?.id;

    // Show loading indicator
    const exportBtn = document.querySelector('#trade-history .btn-secondary');
    const originalText = exportBtn.textContent;
    exportBtn.textContent = 'Exporting...';
    exportBtn.disabled = true;

    // Collect all trades (handle pagination)
    const allTrades = [];
    let page = 1;
    let hasMorePages = true;

    while (hasMorePages) {
      const endpoint = isAdmin
        ? `/api/trades?mode=${currentMode}&page=${page}&merge_db=1`
        : `/api/user/${userId}/trades?page=${page}&mode=${currentMode}`;

      const data = await fetchJson(endpoint);

      if (!data || data.error || !Array.isArray(data.trades)) {
        throw new Error(data?.error || 'Invalid response');
      }

      allTrades.push(...data.trades);

      // Check if there are more pages
      hasMorePages = page < data.total_pages;
      page++;
    }

    if (allTrades.length === 0) {
      alert('No trades to export');
      return;
    }

    // Convert to CSV
    const csvContent = convertTradesToCSV(allTrades);

    // Download CSV file
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `trades_${currentMode}_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

  } catch (error) {
    console.error('Error exporting trades:', error);
    alert('Failed to export trades. Please try again.');
  } finally {
    // Restore button state
    const exportBtn = document.querySelector('#trade-history .btn-secondary');
    if (exportBtn) {
      exportBtn.textContent = originalText;
      exportBtn.disabled = false;
    }
  }
}

function convertTradesToCSV(trades) {
  const headers = ['Date', 'Symbol', 'Side', 'Quantity', 'Entry Price', 'P&L', 'Status'];
  let csv = headers.join(',') + '\n';

  trades.forEach(trade => {
    const timestamp = new Date(trade.timestamp);
    const dateString = timestamp.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });

    const pnl = Number(trade.pnl) || 0;
    const pnlText = pnl >= 0 ? `$${pnl.toFixed(4)}` : `-$${Math.abs(pnl).toFixed(4)}`;

    const quantity = Number(trade.quantity || trade.qty) || 0;
    const entryPrice = Number(trade.entry_price ?? trade.price ?? trade.fill_price) || 0;
    const status = trade.status || trade.state || 'unknown';
    const side = trade.side || trade.position_side || 'N/A';
    const symbol = trade.symbol || trade.ticker || 'N/A';

    const row = [
      `"${dateString}"`,
      `"${symbol}"`,
      `"${side}"`,
      quantity.toFixed(4),
      entryPrice.toFixed(4),
      `"${pnlText}"`,
      `"${status}"`
    ];

    csv += row.join(',') + '\n';
  });

  return csv;
}

// Initialize trade history page
export function initTradeHistory() {
  // Load trade history when page becomes visible
  window.addEventListener('dashboard:trade-history-visible', () => {
    loadTradeHistory();
  });

  // Setup filters and pagination
  setupFilters();

// Handle export button
  const exportBtn = document.getElementById('export-trades-btn');
  if (exportBtn) {
    exportBtn.addEventListener('click', async () => {
      try {
        await exportTradesToCSV();
      } catch (error) {
        console.error('Error exporting trades:', error);
        alert('Failed to export trades. Please try again.');
      }
    });
  }
}