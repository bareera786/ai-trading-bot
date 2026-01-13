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

let currentTrades = [];

export async function loadTradeHistory() {
  try {
    let user;
    try {
      user = await fetchJson('/api/current_user');
    } catch (authError) {
      if (authError.message.includes('Authentication required')) {
        // Redirect to login page
        window.location.href = '/login';
        return;
      }
      throw authError;
    }
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

    // Ensure we operate on a shallow copy and sort by opened_at from canonical schema
    const trades = Array.isArray(data.trades) ? [...data.trades] : [];
    trades.sort((a, b) => {
      const ta = parseTimestampToMs(a?.opened_at) || 0;
      const tb = parseTimestampToMs(b?.opened_at) || 0;
      // Descending (newest first)
      if (tb === ta) {
        // stable-ish tie-breaker: prefer larger trade id when available
        const ida = Number(a?.id ?? 0);
        const idb = Number(b?.id ?? 0);
        return idb - ida;
      }
      return tb - ta;
    });

    currentTrades = trades;
    populateTradeHistoryTable(trades);

    // Add resize listener for responsive rendering
    if (!window.tradeHistoryResizeListener) {
      window.tradeHistoryResizeListener = () => {
        populateTradeHistoryTable(currentTrades);
      };
      window.addEventListener('resize', window.tradeHistoryResizeListener);
    }
  } catch (error) {
    console.error('Error loading trade history:', error);
    renderEmptyState('Unable to load trade history');
  }
}

function populateTradeHistoryTable(trades) {
  const tbody = document.getElementById('trade-history-table');
  const mobileContainer = document.getElementById('trade-history-mobile');
  const isMobile = window.innerWidth <= 768;

  // Clear both containers
  if (tbody) tbody.innerHTML = '';
  if (mobileContainer) mobileContainer.innerHTML = '';

  if (!trades || trades.length === 0) {
    if (!isMobile && tbody) {
      const row = document.createElement('tr');
      row.innerHTML = '<td colspan="16" style="text-align: center; padding: 2rem;">No trades found</td>';
      tbody.appendChild(row);
    } else if (isMobile && mobileContainer) {
      mobileContainer.innerHTML = '<div style="text-align: center; padding: 2rem; color: var(--text-secondary);">No trades found</div>';
    }
    return;
  }

  if (isMobile && mobileContainer) {
    // Render mobile cards
    trades.forEach(trade => renderMobileTradeCard(trade, mobileContainer));
  } else if (!isMobile && tbody) {
    // Render table rows
    trades.forEach(trade => renderTradeTableRow(trade, tbody));
  }
}

function renderTradeTableRow(trade, tbody) {
  const row = document.createElement('tr');

  // Use canonical schema: opened_at for timestamp
  const timestamp = new Date(parseTimestampToMs(trade.opened_at));
  const dateString = timestamp.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });

  // Use canonical schema: PnL is provided by backend, null for OPEN trades
  const pnl = trade.pnl;
  const hasPnl = typeof pnl === 'number' && Number.isFinite(pnl);
  const pnlClass = hasPnl ? (pnl >= 0 ? 'text-success' : 'text-danger') : 'text-muted';
  // Only show PnL for CLOSED trades - for OPEN trades, show '—'
  const pnlText = (hasPnl && trade.status === 'CLOSED')
    ? (pnl >= 0 ? `+$${pnl.toFixed(4)}` : `-$${Math.abs(pnl).toFixed(4)}`)
    : '—';

  const quantity = toSafeNumber(trade.quantity, 0);
  const entryPrice = toSafeNumber(trade.entry_price, 0);
  const status = trade.status || 'OPEN';
  const isClosed = status === 'CLOSED';
  const side = trade.side || 'N/A';
  const symbol = trade.symbol || 'N/A';

  const marketType = String(trade?.market_type || '').toUpperCase();

  let tradeTypeLabel = marketType || 'SPOT';
  let tradeTypeClass = marketType.toLowerCase() || 'spot';

  const leverage = (marketType === 'FUTURES') && trade.leverage
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
    <td class="trade-col-execmode">${trade.market_type || ''}</td>
    <td class="trade-col-market">${marketType || ''}</td>
    <td class="trade-col-exchange">-</td>
    <td class="trade-col-margin">-</td>
    <td class="trade-col-reduce">-</td>
    <td class="trade-col-order">-</td>
    <td class="trade-col-num ${pnlClass}">${pnlText}</td>
    <td class="trade-col-status"><span class="status-indicator status-${getStatusClass(status)}">${status}</span></td>
    <td class="trade-col-actions">
      <button class="btn btn-secondary btn-sm trade-detail-btn">Details</button>
    </td>
  `;

  row.style.cursor = 'pointer';
  row.addEventListener('click', (e) => {
    if (e.target.closest('button')) return;
    showTradeDetail(trade);
  });

  const detailBtn = row.querySelector('.trade-detail-btn');
  if (detailBtn) {
    detailBtn.addEventListener('click', () => showTradeDetail(trade));
  }

  tbody.appendChild(row);
}

function renderMobileTradeCard(trade, container) {
  // Use canonical schema: opened_at for timestamp
  const timestamp = new Date(parseTimestampToMs(trade.opened_at));
  const dateString = timestamp.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });

  // Use canonical schema: PnL is provided by backend, null for OPEN trades
  const pnl = trade.pnl;
  const hasPnl = typeof pnl === 'number' && Number.isFinite(pnl);
  const quantity = toSafeNumber(trade.quantity, 0);
  const entryPrice = toSafeNumber(trade.entry_price, 0);
  const status = trade.status || 'OPEN';
  const isClosed = status === 'CLOSED';
  const side = trade.side || 'N/A';
  const symbol = trade.symbol || 'N/A';

  const card = document.createElement('div');
  card.className = 'mobile-trade-card';

  card.innerHTML = `
    <div class="mobile-trade-card-header">
      <div>
        <div class="mobile-trade-card-symbol">${symbol}</div>
        <div class="mobile-trade-card-meta">${dateString} • ${side}</div>
      </div>
      <div class="mobile-trade-card-status status-${isClosed ? 'closed' : 'open'}">
        ${status}
      </div>
    </div>
    <div class="mobile-trade-card-details">
      <div>
        <div class="mobile-trade-card-price">$${entryPrice.toFixed(4)}</div>
        <div style="font-size: var(--font-size-sm); color: var(--text-secondary);">
          Qty: ${quantity.toFixed(4)}
        </div>
      </div>
      ${isClosed && hasPnl ? `
        <div style="text-align: right;">
          <div style="font-size: var(--font-size-md); font-weight: var(--font-weight-medium); color: ${pnl >= 0 ? 'var(--success-text)' : 'var(--danger-text)'}">
            ${pnl >= 0 ? '+' : ''}$${pnl.toFixed(4)}
          </div>
        </div>
      ` : ''}
    </div>
    <div class="mobile-trade-card-actions">
      <button class="btn btn-secondary btn-sm trade-detail-btn">Details</button>
    </div>
  `;

  const detailBtn = card.querySelector('.trade-detail-btn');
  if (detailBtn) {
    detailBtn.addEventListener('click', () => showTradeDetail(trade));
  }

  container.appendChild(card);
}

function showTradeDetail(trade) {
  const modal = document.getElementById('trade-detail-modal');
  if (!modal) {
    alert('Trade details:\n' + JSON.stringify(trade, null, 2));
    return;
  }

  let el = modal.querySelector('.trade-detail-timestamp');
  // Use canonical schema: opened_at for timestamp
  if (el) el.textContent = new Date(parseTimestampToMs(trade.opened_at)).toLocaleString();

  el = modal.querySelector('.trade-detail-symbol');
  if (el) el.textContent = trade.symbol || 'N/A';

  el = modal.querySelector('.trade-detail-side');
  if (el) el.textContent = trade.side || 'N/A';

  el = modal.querySelector('.trade-detail-qty');
  if (el) el.textContent = toSafeNumber(trade.quantity, 0).toFixed(8);

  el = modal.querySelector('.trade-detail-entry');
  // Use canonical schema: entry_price
  if (el) el.textContent = toSafeNumber(trade.entry_price, 0).toFixed(8);

  el = modal.querySelector('.trade-detail-exit');
  if (el) {
    const status = trade.status || 'OPEN';
    const exit = toSafeNumber(trade.exit_price, 0);
    if (status === 'OPEN' && exit === 0) {
      el.textContent = '—';
    } else {
      el.textContent = exit.toFixed(8);
    }
  }

  el = modal.querySelector('.trade-detail-pnl');
  if (el) {
    // Use canonical schema: PnL is provided by backend, null for OPEN trades
    const pnl = trade.pnl;
    const hasPnl = typeof pnl === 'number' && Number.isFinite(pnl);
    el.textContent = hasPnl ? pnl.toFixed(8) : '—';
  }

  el = modal.querySelector('.trade-detail-status');
  if (el) el.textContent = trade.status || 'OPEN';

  // Structured metadata fields for clarity
  el = modal.querySelector('.trade-detail-execmode');
  if (el) el.textContent = trade.market_type || '';

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
    let user;
    try {
      user = await fetchJson('/api/current_user');
    } catch (authError) {
      if (authError.message.includes('Authentication required')) {
        // Redirect to login page
        window.location.href = '/login';
        return;
      }
      throw authError;
    }
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
        let user;
        try {
          user = await fetchJson('/api/current_user');
        } catch (authError) {
          if (authError.message.includes('Authentication required')) {
            // Redirect to login page
            window.location.href = '/login';
            return;
          }
          throw authError;
        }
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
        let user;
        try {
          user = await fetchJson('/api/current_user');
        } catch (authError) {
          if (authError.message.includes('Authentication required')) {
            // Redirect to login page
            window.location.href = '/login';
            return;
          }
          throw authError;
        }
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
