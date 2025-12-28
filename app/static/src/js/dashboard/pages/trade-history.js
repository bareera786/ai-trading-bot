import { fetchJson } from '../utils/network.js';

let currentPage = 1;
let currentMode = 'ultimate';

export async function loadTradeHistory() {
  try {
    const user = await fetchJson('/api/current_user');
    const isAdmin = Boolean(user?.is_admin);
    const userId = user?.id;

    // Admins can merge DB + live trades; regular users should pull their own persisted trades
    const endpoint = isAdmin
      ? `/api/trades?mode=${currentMode}&page=${currentPage}&merge_db=1`
      : `/api/user/${userId}/trades?page=${currentPage}&mode=${currentMode}`;

    const data = await fetchJson(endpoint);

    if (!data || data.error || !Array.isArray(data.trades)) {
      console.error('Failed to load trade history:', data?.error || 'Invalid response');
      renderEmptyState('Unable to load trade history');
      return;
    }

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
    row.innerHTML = '<td colspan="7" style="text-align: center; padding: 2rem;">No trades found</td>';
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

    row.innerHTML = `
      <td>${dateString}</td>
      <td>${symbol}</td>
      <td>${side}</td>
      <td>${quantity.toFixed(4)}</td>
      <td>$${entryPrice.toFixed(4)}</td>
      <td class="${pnlClass}">${pnlText}</td>
      <td><span class="status-indicator status-${getStatusClass(status)}">${status}</span></td>
    `;

    tbody.appendChild(row);
  });
}

function renderEmptyState(message) {
  const tbody = document.getElementById('trade-history-table');
  if (!tbody) return;
  tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 2rem;">${message}</td></tr>`;
}

function getStatusClass(status) {
  switch (status?.toLowerCase()) {
    case 'filled':
    case 'closed':
      return 'success';
    default:
      return 'warning';
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

  // Handle filter changes
  const filterSelect = document.querySelector('#trade-history .form-input');
  if (filterSelect) {
    filterSelect.addEventListener('change', (e) => {
      // For now, just reload - in future could filter client-side
      loadTradeHistory();
    });
  }

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