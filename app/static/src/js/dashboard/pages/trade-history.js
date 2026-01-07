import { fetchJson } from '../utils/network.js';

let currentPage = 1;
let currentFilters = {
  symbol: '',
  days: '',
  type: 'all',
};
let totalPages = 1;
const availableSymbols = new Set();
let currentMode = 'ultimate';

const toSafeNumber = (value, fallback = 0) => {
  const n = Number(value ?? fallback);
  return Number.isFinite(n) ? n : fallback;
};

export async function loadTradeHistory() {
  try {
    const user = await fetchJson('/api/current_user');
    const isAdmin = Boolean(user?.is_admin);
    const userId = user?.id;

    const params = new URLSearchParams({
      mode: currentMode,
      page: String(currentPage),
      merge_db: isAdmin ? '1' : '0',
    });

    if (currentFilters.symbol) params.append('symbol', currentFilters.symbol);
    if (currentFilters.days) params.append('days', currentFilters.days);

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

    totalPages = data.total_pages || 1;
    updatePaginationControls(data.current_page || currentPage, totalPages);

    data.trades.forEach(trade => {
      if (trade?.symbol) availableSymbols.add(trade.symbol);
    });
    updateSymbolFilter();

    const trades = Array.isArray(data.trades) ? [...data.trades] : [];
    trades.sort((a, b) => {
      const ta = new Date(a?.timestamp || 0).getTime();
      const tb = new Date(b?.timestamp || 0).getTime();
      return tb - ta;
    });

    populateTradeHistoryTable(trades);
  } catch (error) {
    console.error('Error loading trade history:', error);
    renderEmptyState('Unable to load trade history');
  }
}

function populateTradeHistoryTable(trades) {
  const tbody = document.getElementById('trade-history-table');
  if (!tbody) return;

  tbody.innerHTML = '';

  if (!trades || trades.length === 0) {
    const row = document.createElement('tr');
    row.innerHTML = '<td colspan="10" style="text-align: center; padding: 2rem;">No trades found</td>';
    tbody.appendChild(row);
    return;
  }

  trades.forEach(trade => {
    const row = document.createElement('tr');

    const timestamp = new Date(trade.timestamp || Date.now());
    const dateString = timestamp.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });

    const pnl = toSafeNumber(trade.pnl, 0);
    const pnlClass = pnl >= 0 ? 'text-success' : 'text-danger';
    const pnlText = pnl >= 0 ? `+$${pnl.toFixed(4)}` : `-$${Math.abs(pnl).toFixed(4)}`;

    const quantity = toSafeNumber(trade.quantity ?? trade.qty, 0);
    const entryPrice = toSafeNumber(trade.entry_price ?? trade.price ?? trade.fill_price, 0);
    const status = trade.status || trade.state || 'unknown';
    const normalizedStatus = String(status || 'unknown').toLowerCase();
    const isClosed = normalizedStatus === 'filled' || normalizedStatus === 'closed' || normalizedStatus === 'success';
    const side = trade.side || trade.position_side || 'N/A';
    const symbol = trade.symbol || trade.ticker || 'N/A';

    const tradeType = trade.execution_mode === 'futures'
      ? 'Futures'
      : trade.execution_mode === 'real'
        ? 'Spot'
        : 'Paper';

    const leverage = trade.leverage ? `${trade.leverage}x` : '-';

    row.classList.add('trade-row', isClosed ? 'trade-row-closed' : 'trade-row-open');

    row.innerHTML = `
      <td class="trade-col-date">${dateString}</td>
      <td class="trade-col-symbol">${symbol}</td>
      <td class="trade-col-type"><span class="trade-type-${tradeType.toLowerCase()}">${tradeType}</span></td>
      <td class="trade-col-side">${side}</td>
      <td class="trade-col-num">${quantity.toFixed(4)}</td>
      <td class="trade-col-num">$${entryPrice.toFixed(4)}</td>
      <td class="trade-col-num">${leverage}</td>
      <td class="trade-col-num ${pnlClass}">${pnlText}</td>
      <td class="trade-col-status"><span class="status-indicator status-${getStatusClass(status)}">${status}</span></td>
      <td class="trade-col-actions"><button class="btn btn-secondary btn-sm trade-detail-btn">Details</button></td>
    `;

    row.style.cursor = 'pointer';
    row.addEventListener('click', () => showTradeDetail(trade));

    const detailBtn = row.querySelector('.trade-detail-btn');
    if (detailBtn) {
      detailBtn.addEventListener('click', e => {
        e.stopPropagation();
        showTradeDetail(trade);
      });
    }

    tbody.appendChild(row);
  });
}

function showTradeDetail(trade) {
  const modal = document.getElementById('trade-detail-modal');
  if (!modal) {
    alert('Trade details:\n' + JSON.stringify(trade, null, 2));
    return;
  }

  let el = modal.querySelector('.trade-detail-timestamp');
  if (el) el.textContent = new Date(trade.timestamp || Date.now()).toLocaleString();

  el = modal.querySelector('.trade-detail-symbol');
  if (el) el.textContent = trade.symbol || trade.ticker || 'N/A';

  el = modal.querySelector('.trade-detail-side');
  if (el) el.textContent = trade.side || trade.position_side || 'N/A';

  el = modal.querySelector('.trade-detail-qty');
  if (el) el.textContent = toSafeNumber(trade.quantity ?? trade.qty, 0).toFixed(8);

  el = modal.querySelector('.trade-detail-entry');
  if (el) el.textContent = toSafeNumber(trade.entry_price ?? trade.price ?? trade.fill_price, 0).toFixed(8);

  el = modal.querySelector('.trade-detail-exit');
  if (el) el.textContent = toSafeNumber(trade.exit_price ?? trade.close_price, 0).toFixed(8);

  el = modal.querySelector('.trade-detail-pnl');
  if (el) el.textContent = toSafeNumber(trade.pnl, 0).toFixed(8);

  el = modal.querySelector('.trade-detail-status');
  if (el) el.textContent = trade.status || trade.state || 'N/A';

  el = modal.querySelector('.trade-detail-meta');
  if (el) el.textContent = JSON.stringify(trade, null, 2);

  modal.style.display = 'flex';
}

function renderEmptyState(message) {
  const tbody = document.getElementById('trade-history-table');
  if (!tbody) return;
  tbody.innerHTML = `<tr><td colspan="10" style="text-align:center; padding: 2rem;">${message}</td></tr>`;
}

function getStatusClass(status) {
  switch ((status || '').toLowerCase()) {
    case 'filled':
    case 'closed':
    case 'success':
      return 'success';
    case 'failed':
    case 'error':
      return 'danger';
    default:
      return 'neutral';
  }
}

function updatePaginationControls(current, total) {
  const paginationDiv = document.getElementById('trade-pagination');
  const pageInfo = document.getElementById('page-info');
  const prevBtn = document.getElementById('prev-page-btn');
  const nextBtn = document.getElementById('next-page-btn');

  if (!paginationDiv || !pageInfo || !prevBtn || !nextBtn) return;

  if (total > 1) {
    paginationDiv.style.display = 'block';
    pageInfo.textContent = `Page ${current} of ${total}`;
    prevBtn.disabled = current <= 1;
    nextBtn.disabled = current >= total;
  } else {
    paginationDiv.style.display = 'none';
  }
}

function updateSymbolFilter() {
  const symbolSelect = document.getElementById('trade-symbol-filter');
  if (!symbolSelect) return;

  while (symbolSelect.options.length > 1) symbolSelect.remove(1);

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
    filterSelect.addEventListener('change', e => {
      currentFilters.type = e.target.value;
      currentPage = 1;
      loadTradeHistory();
    });
  }

  if (symbolSelect) {
    symbolSelect.addEventListener('change', e => {
      currentFilters.symbol = e.target.value;
      currentPage = 1;
      loadTradeHistory();
    });
  }

  if (daysSelect) {
    daysSelect.addEventListener('change', e => {
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

export function convertTradesToCSV(trades) {
  const headers = ['Date', 'Symbol', 'Side', 'Quantity', 'Entry Price', 'P&L', 'Status'];
  const lines = [headers.join(',')];

  (trades || []).forEach(trade => {
    const timestamp = new Date(trade.timestamp || Date.now());
    const dateString = timestamp.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });

    const pnl = toSafeNumber(trade.pnl, 0);
    const pnlText = pnl >= 0 ? `$${pnl.toFixed(4)}` : `-$${Math.abs(pnl).toFixed(4)}`;

    const quantity = toSafeNumber(trade.quantity ?? trade.qty, 0);
    const entryPrice = toSafeNumber(trade.entry_price ?? trade.price ?? trade.fill_price, 0);
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
      `"${status}"`,
    ];

    lines.push(row.join(','));
  });

  return lines.join('\n');
}

async function exportTradesToCSV() {
  let exportBtn;
  let originalText;

  try {
    const user = await fetchJson('/api/current_user');
    const isAdmin = Boolean(user?.is_admin);
    const userId = user?.id;

    exportBtn = document.getElementById('export-trades-btn') || document.querySelector('#trade-history .btn-secondary');
    if (exportBtn) {
      originalText = exportBtn.textContent;
      exportBtn.textContent = 'Exporting...';
      exportBtn.disabled = true;
    }

    const allTrades = [];
    let page = 1;
    let hasMorePages = true;

    while (hasMorePages) {
      const endpoint = isAdmin
        ? `/api/trades?mode=${encodeURIComponent(currentMode)}&page=${page}&merge_db=1`
        : `/api/user/${userId}/trades?page=${page}&mode=${encodeURIComponent(currentMode)}`;

      const data = await fetchJson(endpoint);
      if (!data || data.error || !Array.isArray(data.trades)) {
        throw new Error(data?.error || 'Invalid response');
      }

      allTrades.push(...data.trades);
      hasMorePages = page < (data.total_pages || 1);
      page++;
    }

    if (allTrades.length === 0) {
      alert('No trades to export');
      return;
    }

    const csvContent = convertTradesToCSV(allTrades);
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
    if (exportBtn) {
      exportBtn.textContent = originalText || 'Export';
      exportBtn.disabled = false;
    }
  }
}

export function initTradeHistory() {
  window.addEventListener('dashboard:trade-history-visible', () => {
    loadTradeHistory();
  });

  setupFilters();

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

  const clearBtn = document.getElementById('clear-trades-btn');
  if (clearBtn) {
    clearBtn.addEventListener('click', async () => {
      try {
        const user = await fetchJson('/api/current_user');
        const userId = user?.id;
        if (!userId) {
          alert('Unable to determine current user.');
          return;
        }

        const confirmed = window.confirm(
          'This will permanently delete YOUR trade history. This cannot be undone. Continue?'
        );
        if (!confirmed) return;

        clearBtn.disabled = true;
        const originalText = clearBtn.textContent;
        clearBtn.textContent = 'Clearing...';

        const resp = await fetchJson(`/api/user/${userId}/trades/clear`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        });

        if (!resp || resp.success !== true) {
          alert(resp?.error || 'Failed to clear trade history');
          return;
        }

        availableSymbols.clear();
        currentPage = 1;
        await loadTradeHistory();
        alert(`Cleared ${resp.deleted || 0} trade(s).`);
      } catch (error) {
        console.error('Error clearing trades:', error);
        alert('Failed to clear trade history. Please try again.');
      } finally {
        clearBtn.disabled = false;
        if (clearBtn.textContent === 'Clearing...') {
          clearBtn.textContent = 'Clear My History';
        }
      }
    });
  }
}

// Back-compat hook used by older templates/buttons.
window.showTradeDetails = function (trade) {
  showTradeDetail(trade);
};
