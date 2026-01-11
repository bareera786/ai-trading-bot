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

// Parse a timestamp value (string or number) into milliseconds since epoch.
// Handles ISO strings, integer/float epoch (seconds or milliseconds), and
// digit-only strings. Returns a numeric ms timestamp.
const parseTimestampToMs = (ts) => {
  if (ts === null || ts === undefined || ts === '') return Date.now();
  if (typeof ts === 'number') {
    const n = ts;
    if (n > 1e12) return n; // probably milliseconds
    if (n > 1e9) return n * 1000; // seconds -> ms
    return n * 1000;
  }
  if (typeof ts === 'string') {
    const s = ts.trim();
    if (/^\d+$/.test(s)) {
      const n = Number(s);
      if (n > 1e12) return n;
      if (n > 1e9) return n * 1000;
      return n * 1000;
    }
    const parsed = Date.parse(s);
    if (!Number.isNaN(parsed)) return parsed;
    return Date.now();
  }
  return Date.now();
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

    // Ensure we operate on a shallow copy and sort by the most reliable
    // timestamp candidates (timestamp, entry_timestamp, created_at).
    const trades = Array.isArray(data.trades) ? [...data.trades] : [];
    trades.sort((a, b) => {
      const ta = Math.max(
        parseTimestampToMs(a?.timestamp),
        parseTimestampToMs(a?.entry_timestamp),
        parseTimestampToMs(a?.created_at),
        0
      );
      const tb = Math.max(
        parseTimestampToMs(b?.timestamp),
        parseTimestampToMs(b?.entry_timestamp),
        parseTimestampToMs(b?.created_at),
        0
      );
      // Descending (newest first)
      if (tb === ta) {
        // stable-ish tie-breaker: prefer larger trade id when available
        const ida = Number(a?.trade_id ?? a?.id ?? 0);
        const idb = Number(b?.trade_id ?? b?.id ?? 0);
        return idb - ida;
      }
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
    // Updated colspan to match expanded column count (16)
    row.innerHTML = '<td colspan="16" style="text-align: center; padding: 2rem;">No trades found</td>';
    tbody.appendChild(row);
    return;
  }

  trades.forEach(trade => {
    const row = document.createElement('tr');

    const timestamp = new Date(parseTimestampToMs(trade.timestamp));
    const dateString = timestamp.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });

    const hasPnl = typeof trade?.pnl === 'number' && Number.isFinite(trade.pnl);
    const rawExit = trade.exit_price ?? trade.close_price ?? null;
    const hasExit = rawExit !== null && rawExit !== undefined && rawExit !== 0;
    const pnl = hasPnl ? trade.pnl : null;
    const pnlClass = hasPnl ? (pnl >= 0 ? 'text-success' : 'text-danger') : 'text-muted';
    const pnlText = hasPnl
      ? (pnl >= 0 ? `+$${pnl.toFixed(4)}` : `-$${Math.abs(pnl).toFixed(4)}`)
      : '—';

    const quantity = toSafeNumber(trade.quantity ?? trade.qty, 0);
    const entryPrice = toSafeNumber(trade.entry_price ?? trade.price ?? trade.fill_price, 0);
    const status = trade.status || trade.state || 'unknown';
    const normalizedStatus = String(status || 'unknown').toLowerCase();
    const isClosed = normalizedStatus === 'filled' || normalizedStatus === 'closed' || normalizedStatus === 'success';
    const side = trade.side || trade.position_side || 'N/A';
    const symbol = trade.symbol || trade.ticker || 'N/A';

    const marketType = String(trade?.market_type || '').toUpperCase();
    const exchange = String(trade?.exchange || '').toUpperCase();

    let tradeTypeLabel = '—';
    let tradeTypeClass = 'unknown';

    if (marketType === 'FUTURES' || marketType === 'SPOT') {
      tradeTypeLabel = exchange ? `${marketType} / ${exchange}` : marketType;
      tradeTypeClass = marketType.toLowerCase();
    } else if (trade?.execution_mode) {
      const mode = String(trade.execution_mode).toUpperCase();
      tradeTypeLabel = mode;
      tradeTypeClass = mode === 'PAPER' ? 'paper' : mode === 'FUTURES' ? 'futures' : 'unknown';
    }

    const leverage = (marketType === 'FUTURES' || String(trade?.execution_mode || '').toLowerCase() === 'futures') && trade.leverage
      ? `${trade.leverage}x`
      : '-';

    row.classList.add('trade-row', isClosed ? 'trade-row-closed' : 'trade-row-open');

    row.innerHTML = `
      <td class="trade-col-date">${dateString}</td>
      <td class="trade-col-symbol">${symbol}</td>
      <td class="trade-col-type"><span class="trade-type-${tradeTypeClass}">${tradeTypeLabel}</span></td>
      <td class="trade-col-side">${side}</td>
      <td class="trade-col-num">${quantity.toFixed(4)}</td>
      <td class="trade-col-num">$${entryPrice.toFixed(4)}</td>
      <td class="trade-col-num">${leverage}</td>
      <td class="trade-col-execmode">${trade.execution_mode || ''}</td>
      <td class="trade-col-market">${marketType || ''}</td>
      <td class="trade-col-exchange">${exchange || ''}</td>
      <td class="trade-col-margin">${trade.margin_type || ''}</td>
      <td class="trade-col-reduce">${trade.reduce_only ? String(trade.reduce_only) : ''}</td>
      <td class="trade-col-order">${trade.real_order_id || trade.order_id || ''}</td>
      <td class="trade-col-num ${pnlClass}">${pnlText}</td>
      <td class="trade-col-status"><span class="status-indicator status-${getStatusClass(status)}">${status}</span></td>
      <td class="trade-col-actions">
        <button class="btn btn-secondary btn-sm trade-detail-btn" ${(!hasExit && !hasPnl) ? 'disabled title="Details disabled: no exit price or P&L available"' : ''}>Details</button>
      </td>
    `;

    row.style.cursor = 'pointer';
    row.addEventListener('click', () => showTradeDetail(trade));

    const detailBtn = row.querySelector('.trade-detail-btn');
    if (detailBtn) {
      // If disabled, do not open modal from the button (but keep row click behavior).
      detailBtn.addEventListener('click', e => {
        e.stopPropagation();
        if (detailBtn.disabled) return;
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
  if (el) el.textContent = new Date(parseTimestampToMs(trade.timestamp)).toLocaleString();

  el = modal.querySelector('.trade-detail-symbol');
  if (el) el.textContent = trade.symbol || trade.ticker || 'N/A';

  el = modal.querySelector('.trade-detail-side');
  if (el) el.textContent = trade.side || trade.position_side || 'N/A';

  el = modal.querySelector('.trade-detail-qty');
  if (el) el.textContent = toSafeNumber(trade.quantity ?? trade.qty, 0).toFixed(8);

  el = modal.querySelector('.trade-detail-entry');
  if (el) el.textContent = toSafeNumber(trade.entry_price ?? trade.price ?? trade.fill_price, 0).toFixed(8);

  el = modal.querySelector('.trade-detail-exit');
  if (el) {
    const status = String(trade.status || trade.state || '').toUpperCase();
    const rawExit = trade.exit_price ?? trade.close_price;
    const exit = toSafeNumber(rawExit, 0);
    if (status === 'OPEN' && exit === 0) {
      el.textContent = '—';
    } else {
      el.textContent = exit.toFixed(8);
    }
  }

  el = modal.querySelector('.trade-detail-pnl');
  if (el) {
    const hasPnl = typeof trade?.pnl === 'number' && Number.isFinite(trade.pnl);
    el.textContent = hasPnl ? trade.pnl.toFixed(8) : '—';
  }

  el = modal.querySelector('.trade-detail-status');
  if (el) el.textContent = trade.status || trade.state || 'N/A';

  // Structured metadata fields for clarity
  el = modal.querySelector('.trade-detail-execmode');
  if (el) el.textContent = trade.execution_mode || trade.mode || '';

  el = modal.querySelector('.trade-detail-market');
  if (el) el.textContent = trade.market_type || '';

  el = modal.querySelector('.trade-detail-exchange');
  if (el) el.textContent = trade.exchange || '';

  el = modal.querySelector('.trade-detail-margin');
  if (el) el.textContent = trade.margin_type || '';

  el = modal.querySelector('.trade-detail-reduce');
  if (el) el.textContent = trade.reduce_only ? String(trade.reduce_only) : '';

  el = modal.querySelector('.trade-detail-order');
  if (el) el.textContent = trade.real_order_id || trade.order_id || '';

  el = modal.querySelector('.trade-detail-meta');
  if (el) el.textContent = JSON.stringify(trade, null, 2);

  modal.style.display = 'flex';
}

function renderEmptyState(message) {
  const tbody = document.getElementById('trade-history-table');
  if (!tbody) return;
  tbody.innerHTML = `<tr><td colspan="16" style="text-align:center; padding: 2rem;">${message}</td></tr>`;
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
  const headers = [
    'Date',
    'Symbol',
    'Type',
    'Side',
    'Quantity',
    'Entry Price',
    'Leverage',
    'Execution Mode',
    'Market Type',
    'Exchange',
    'Margin Type',
    'Reduce Only',
    'Order ID',
    'P&L',
    'Status',
  ];
  const lines = [headers.join(',')];

  (trades || []).forEach(trade => {
    const timestamp = new Date(parseTimestampToMs(trade.timestamp));
    const dateString = timestamp.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });

    const hasPnl = typeof trade?.pnl === 'number' && Number.isFinite(trade.pnl);
    const pnlText = hasPnl ? (trade.pnl >= 0 ? `$${trade.pnl.toFixed(4)}` : `-$${Math.abs(trade.pnl).toFixed(4)}`) : '';

    const quantity = toSafeNumber(trade.quantity ?? trade.qty, 0);
    const entryPrice = toSafeNumber(trade.entry_price ?? trade.price ?? trade.fill_price, 0);
    const status = trade.status || trade.state || 'unknown';
    const side = trade.side || trade.position_side || 'N/A';
    const symbol = trade.symbol || trade.ticker || 'N/A';
    const typeLabel = (trade.market_type || trade.execution_mode || '').toString();
    const leverage = trade.leverage ? `${trade.leverage}x` : '';

    const row = [
      `"${dateString}"`,
      `"${symbol}"`,
      `"${typeLabel}"`,
      `"${side}"`,
      quantity.toFixed(4),
      entryPrice.toFixed(4),
      `"${leverage}"`,
      `"${trade.execution_mode || ''}"`,
      `"${trade.market_type || ''}"`,
      `"${trade.exchange || ''}"`,
      `"${trade.margin_type || ''}"`,
      `"${trade.reduce_only ? String(trade.reduce_only) : ''}"`,
      `"${trade.real_order_id || trade.order_id || ''}"`,
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
        const isAdmin = Boolean(user?.is_admin);
        const userId = user?.id;
        if (!userId) {
          alert('Unable to determine current user. Please log in again.');
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
        if (isAdmin) {
          alert(
            `Cleared ${resp.deleted || 0} personal trade(s). Admin Trade History includes the system trade log and is not cleared by this action.`
          );
        } else {
          alert(`Cleared ${resp.deleted || 0} trade(s).`);
        }
      } catch (error) {
        console.error('Error clearing trades:', error);
        const msg = String(error?.message || '');
        if (/auth|login|401|403/i.test(msg)) {
          alert('Session expired or access denied. Please log in again.');
        } else {
          alert('Failed to clear trade history. Please try again.');
        }
      } finally {
        clearBtn.disabled = false;
        if (clearBtn.textContent === 'Clearing...') {
          clearBtn.textContent = 'Clear My History';
        }
      }
    });
  }

  const clearSystemBtn = document.getElementById('clear-system-history-btn');
  if (clearSystemBtn) {
    clearSystemBtn.addEventListener('click', async () => {
      try {
        const user = await fetchJson('/api/current_user');
        const isAdmin = Boolean(user?.is_admin);
        if (!isAdmin) {
          alert('Access denied.');
          return;
        }

        const confirmed = window.confirm(
          'This will permanently delete the SYSTEM trade log (bot history). This affects the admin merged view. Continue?'
        );
        if (!confirmed) return;

        clearSystemBtn.disabled = true;
        const originalText = clearSystemBtn.textContent;
        clearSystemBtn.textContent = 'Clearing...';

        const resp = await fetchJson('/api/clear_history', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        });

        if (resp?.error) {
          alert(resp.error);
          return;
        }

        // System history cleared; refresh table.
        currentPage = 1;
        await loadTradeHistory();
        alert(resp?.message || 'System trade history cleared.');
      } catch (error) {
        console.error('Error clearing system history:', error);
        const msg = String(error?.message || '');
        if (/auth|login|401|403/i.test(msg)) {
          alert('Session expired or access denied. Please log in again.');
        } else {
          alert('Failed to clear system history. Please try again.');
        }
      } finally {
        clearSystemBtn.disabled = false;
        if (clearSystemBtn.textContent === 'Clearing...') {
          clearSystemBtn.textContent = 'Clear System History';
        }
      }
    });
  }
}

// Back-compat hook used by older templates/buttons.
window.showTradeDetails = function (trade) {
  showTradeDetail(trade);
};
