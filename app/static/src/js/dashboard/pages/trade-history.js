import { fetchJson } from '../utils/network.js';

let currentPage = 1;
let currentFilters = {
  symbol: '',
  days: '',
  type: 'all',
  mode: 'all'
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
      mode: currentFilters.mode,
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
    const totalTrades = data.total_trades || data.trades.length;
    updatePaginationControls(data.current_page, totalPages, totalTrades);

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
    row.innerHTML = '<td colspan="8" style="text-align: center; padding: 2rem;">No trades found</td>';
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

    // Format P&L with color and percentage
    const pnl = Number(trade.pnl) || 0;
    const pnlPercent = Number(trade.pnl_percent) || 0;
    const pnlClass = pnl >= 0 ? 'text-success' : 'text-danger';
    const pnlPercentClass = pnlPercent >= 0 ? 'text-success' : 'text-danger';
    const pnlText = pnl >= 0 ? `+$${pnl.toFixed(4)}` : `-$${Math.abs(pnl).toFixed(4)}`;
    const pnlPercentText = pnlPercent >= 0 ? `+${pnlPercent.toFixed(2)}%` : `${pnlPercent.toFixed(2)}%`;

    // Determine trade type
    const tradeType = trade.execution_mode === 'futures' ? 'Futures' :
                     trade.execution_mode === 'real' ? 'Spot' : 'Paper';

    // Leverage (only for futures)
    const leverage = trade.leverage ? `${trade.leverage}x` : '-';

    // Strategy and confidence
    const strategy = trade.strategy || trade.action_type || 'Unknown';
    const confidence = trade.confidence ? `${(trade.confidence * 100).toFixed(1)}%` : '-';

    // Entry and exit prices
    const entryPrice = Number(trade.entry_price ?? trade.price ?? trade.fill_price) || 0;
    const exitPrice = Number(trade.exit_price) || 0;

    // Status with better formatting
    const status = trade.status || trade.state || 'unknown';
    const statusClass = getStatusClass(status);

    // Create details button
    const detailsBtn = `<button class="btn btn-secondary" style="padding: 2px 6px; font-size: 11px;" onclick="showTradeDetails(${JSON.stringify(trade).replace(/"/g, '&quot;')})">Details</button>`;

    row.innerHTML = `
      <td>${dateString}</td>
      <td><strong>${trade.symbol || 'N/A'}</strong></td>
      <td><span class="trade-type-${tradeType.toLowerCase()}">${tradeType}</span></td>
      <td>${trade.side || 'N/A'}</td>
      <td>${(Number(trade.quantity || trade.qty) || 0).toFixed(4)}</td>
      <td class="${pnlClass}"><strong>${pnlText}</strong></td>
      <td><span class="status-indicator status-${statusClass}">${status.toUpperCase()}</span></td>
      <td>${detailsBtn}</td>
    `;

    tbody.appendChild(row);
  });
}

function renderEmptyState(message) {
  const tbody = document.getElementById('trade-history-table');
  if (!tbody) return;
  tbody.innerHTML = `<tr><td colspan="14" style="text-align:center; padding: 2rem;">${message}</td></tr>`;
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

function updatePaginationControls(currentPage, totalPages, totalTrades = 0) {
  const paginationDiv = document.getElementById('trade-pagination');
  const pageInfo = document.getElementById('page-info');
  const tradeCount = document.getElementById('trade-count');
  const prevBtn = document.getElementById('prev-page-btn');
  const nextBtn = document.getElementById('next-page-btn');

  if (!paginationDiv || !pageInfo || !prevBtn || !nextBtn) return;

  if (totalPages > 1) {
    paginationDiv.style.display = 'block';
    pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
    prevBtn.disabled = currentPage <= 1;
    nextBtn.disabled = currentPage >= totalPages;
  } else {
    paginationDiv.style.display = 'block'; // Always show for trade count
    pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
    prevBtn.disabled = true;
    nextBtn.disabled = true;
  }

  if (tradeCount) {
    tradeCount.textContent = `Showing ${totalTrades} trades`;
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
        ? `/api/trades?mode=${currentFilters.mode}&page=${page}&merge_db=1`
        : `/api/user/${userId}/trades?page=${page}&mode=${currentFilters.mode}`;

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
  const exportBtn = document.querySelector('#trade-history .btn-secondary');
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

function setupFilters() {
  // Mode filter
  const modeFilter = document.getElementById('trade-mode-filter');
  if (modeFilter) {
    modeFilter.addEventListener('change', (e) => {
      currentFilters.mode = e.target.value;
      currentPage = 1; // Reset to first page
      loadTradeHistory();
    });
  }

  // Type filter
  const typeFilter = document.getElementById('trade-filter-select');
  if (typeFilter) {
    typeFilter.addEventListener('change', (e) => {
      currentFilters.type = e.target.value;
      currentPage = 1; // Reset to first page
      loadTradeHistory();
    });
  }

  // Symbol filter
  const symbolFilter = document.getElementById('trade-symbol-filter');
  if (symbolFilter) {
    symbolFilter.addEventListener('change', (e) => {
      currentFilters.symbol = e.target.value;
      currentPage = 1; // Reset to first page
      loadTradeHistory();
    });
  }

  // Days filter
  const daysFilter = document.getElementById('trade-days-filter');
  if (daysFilter) {
    daysFilter.addEventListener('change', (e) => {
      currentFilters.days = e.target.value;
      currentPage = 1; // Reset to first page
      loadTradeHistory();
    });
  }

  // Refresh button
  const refreshBtn = document.getElementById('refresh-trades-btn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      loadTradeHistory();
    });
  }
}

// Global function for trade details modal
window.showTradeDetails = function(trade) {
  // Create modal HTML
  const modalHtml = `
    <div id="trade-details-modal" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.8); z-index: 2000; display: flex; align-items: center; justify-content: center;">
      <div style="background: var(--bg-card); border-radius: var(--radius-xl); padding: var(--spacing-2xl); max-width: 800px; width: 90%; max-height: 80vh; overflow-y: auto;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--spacing-xl);">
          <h3>Trade Details - ${trade.symbol || 'Unknown'}</h3>
          <button onclick="document.getElementById('trade-details-modal').remove()" style="background: none; border: none; color: var(--text-secondary); font-size: 24px; cursor: pointer;">×</button>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--spacing-lg); margin-bottom: var(--spacing-xl);">
          <div>
            <h4 style="margin-bottom: var(--spacing-md); color: var(--text-primary);">Basic Information</h4>
            <div style="display: grid; grid-template-columns: auto 1fr; gap: var(--spacing-sm); font-size: var(--font-size-sm);">
              <strong>Trade ID:</strong> <span>${trade.trade_id || trade.id || 'N/A'}</span>
              <strong>Timestamp:</strong> <span>${new Date(trade.timestamp).toLocaleString()}</span>
              <strong>Symbol:</strong> <span>${trade.symbol || 'N/A'}</span>
              <strong>Side:</strong> <span>${trade.side || 'N/A'}</span>
              <strong>Type:</strong> <span>${trade.execution_mode === 'futures' ? 'Futures' : trade.execution_mode === 'real' ? 'Spot' : 'Paper'}</span>
              <strong>Status:</strong> <span>${trade.status || 'Unknown'}</span>
              <strong>Strategy:</strong> <span>${trade.strategy || trade.action_type || 'Unknown'}</span>
              <strong>Confidence:</strong> <span>${trade.confidence ? (trade.confidence * 100).toFixed(1) + '%' : 'N/A'}</span>
            </div>
          </div>

          <div>
            <h4 style="margin-bottom: var(--spacing-md); color: var(--text-primary);">Financial Details</h4>
            <div style="display: grid; grid-template-columns: auto 1fr; gap: var(--spacing-sm); font-size: var(--font-size-sm);">
              <strong>Quantity:</strong> <span>${(Number(trade.quantity || trade.qty) || 0).toFixed(6)}</span>
              <strong>Entry Price:</strong> <span>$${(Number(trade.entry_price || trade.price) || 0).toFixed(4)}</span>
              <strong>Exit Price:</strong> <span>${trade.exit_price ? '$' + Number(trade.exit_price).toFixed(4) : 'N/A'}</span>
              <strong>Leverage:</strong> <span>${trade.leverage ? trade.leverage + 'x' : 'None'}</span>
              <strong>P&L ($):</strong> <span style="color: ${(Number(trade.pnl) || 0) >= 0 ? 'var(--success-color)' : 'var(--error-color)'}">${(Number(trade.pnl) || 0) >= 0 ? '+' : ''}$${(Number(trade.pnl) || 0).toFixed(4)}</span>
              <strong>P&L (%):</strong> <span style="color: ${(Number(trade.pnl_percent) || 0) >= 0 ? 'var(--success-color)' : 'var(--error-color)'}">${(Number(trade.pnl_percent) || 0) >= 0 ? '+' : ''}${(Number(trade.pnl_percent) || 0).toFixed(2)}%</span>
              <strong>Total Value:</strong> <span>$${(Number(trade.total_value) || 0).toFixed(4)}</span>
            </div>
          </div>
        </div>

        ${trade.crt_signal ? `
        <div style="margin-bottom: var(--spacing-xl);">
          <h4 style="margin-bottom: var(--spacing-md); color: var(--text-primary);">CRT Signal Details</h4>
          <div style="background: var(--bg-secondary); padding: var(--spacing-md); border-radius: var(--radius-md); font-size: var(--font-size-sm);">
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: var(--spacing-md);">
              <div><strong>Signal:</strong> ${trade.crt_signal.signal || 'N/A'}</div>
              <div><strong>Confidence:</strong> ${trade.crt_signal.confidence ? (trade.crt_signal.confidence * 100).toFixed(1) + '%' : 'N/A'}</div>
              <div><strong>Type:</strong> ${trade.crt_signal.signal_type || 'N/A'}</div>
              <div><strong>Target Price:</strong> ${trade.crt_signal.target_price ? '$' + Number(trade.crt_signal.target_price).toFixed(4) : 'N/A'}</div>
              <div><strong>Stop Loss:</strong> ${trade.crt_signal.stop_loss ? '$' + Number(trade.crt_signal.stop_loss).toFixed(4) : 'N/A'}</div>
              <div><strong>Reason:</strong> ${trade.crt_signal.reason_code || 'N/A'}</div>
            </div>
            ${trade.crt_signal.components ? `
            <div style="margin-top: var(--spacing-md);">
              <strong>Signal Components:</strong>
              <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: var(--spacing-sm); margin-top: var(--spacing-sm);">
                ${Object.entries(trade.crt_signal.components).map(([key, value]) =>
                  `<div>${key}: ${(Number(value) * 100).toFixed(1)}%</div>`
                ).join('')}
              </div>
            </div>
            ` : ''}
          </div>
        </div>
        ` : ''}

        ${trade.signal || trade.market_regime || trade.strategy ? `
        <div style="margin-bottom: var(--spacing-xl);">
          <h4 style="margin-bottom: var(--spacing-md); color: var(--text-primary);">Additional Information</h4>
          <div style="background: var(--bg-secondary); padding: var(--spacing-md); border-radius: var(--radius-md); font-size: var(--font-size-sm);">
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: var(--spacing-md);">
              ${trade.signal ? `<div><strong>Signal:</strong> ${trade.signal}</div>` : ''}
              ${trade.market_regime ? `<div><strong>Market Regime:</strong> ${trade.market_regime}</div>` : ''}
              ${trade.market_stress ? `<div><strong>Market Stress:</strong> ${(trade.market_stress * 100).toFixed(2)}%</div>` : ''}
              ${trade.risk_adjustment ? `<div><strong>Risk Adjustment:</strong> ${trade.risk_adjustment}</div>` : ''}
              ${trade.position_size_percent ? `<div><strong>Position Size:</strong> ${trade.position_size_percent.toFixed(2)}%</div>` : ''}
            </div>
          </div>
        </div>
        ` : ''}
      </div>
    </div>
  `;

  document.body.insertAdjacentHTML('beforeend', modalHtml);
};