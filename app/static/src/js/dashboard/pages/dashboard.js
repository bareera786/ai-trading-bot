import { fetchJson } from '../utils/network.js';

export async function refreshDashboardCards() {
  const data = await fetchJson('/api/status');
  if (!data || data.error) return;

  const portfolioCard = document.querySelector('#dashboard .dashboard-card:nth-child(1) .card-value');
  if (portfolioCard && data.portfolio) {
    const totalValue = (data.portfolio.total_balance || 0) + (data.portfolio.unrealized_pnl || 0);
    portfolioCard.textContent = formatCurrency(totalValue);
  }

  const tradesCard = document.querySelector('#dashboard .dashboard-card:nth-child(2) .card-value');
  if (tradesCard && data.portfolio) {
    const openPositions = Object.keys(data.portfolio.open_positions || {}).length;
    tradesCard.textContent = openPositions;
  }

  const winRateCard = document.querySelector('#dashboard .dashboard-card:nth-child(3) .card-value');
  if (winRateCard && data.performance) {
    const winRate = data.performance.win_rate || 0;
    winRateCard.textContent = `${(winRate * 100).toFixed(1)}%`;
  }

  const systemCard = document.querySelector('#dashboard .dashboard-card:nth-child(4) .card-value .status-indicator');
  if (systemCard && data.system_status) {
    const isOnline = data.system_status.trading_enabled && data.system_status.models_loaded;
    systemCard.className = `status-indicator ${isOnline ? 'status-success' : 'status-warning'}`;
    systemCard.textContent = isOnline ? 'ONLINE' : 'OFFLINE';
  }

  await loadUserDashboardData();
}

export async function refreshRecentActivity() {
  const data = await fetchJson('/api/trades?page=1&limit=10');
  if (!data || data.error || !Array.isArray(data.trades)) return;
  const tbody = document.getElementById('recent-activity');
  if (!tbody) return;
  tbody.innerHTML = '';
  data.trades.slice(0, 5).forEach((trade) => {
    const row = document.createElement('tr');
    const timestamp = new Date(trade.timestamp * 1000);
    const timeString = timestamp.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
    row.innerHTML = `
      <td>${timeString}</td>
      <td>${trade.symbol || 'N/A'}</td>
      <td>${trade.side || 'N/A'}</td>
      <td>$${(trade.price || 0).toFixed(2)}</td>
      <td><span class="status-indicator status-${trade.status === 'filled' ? 'success' : 'warning'}">${trade.status || 'unknown'}</span></td>
    `;
    tbody.appendChild(row);
  });
}

async function loadUserDashboardData() {
  const user = await fetchJson('/api/current_user');
  if (!user || !user.id) return;
  const portfolio = await fetchJson(`/api/portfolio/user/${user.id}`);
  if (portfolio) {
    updateUserPortfolioWidgets(portfolio);
  }
  const trades = await fetchJson('/api/trades?limit=10');
  if (trades && Array.isArray(trades.trades)) {
    updateUserTradesTable(trades.trades);
  }
}

function updateUserPortfolioWidgets(portfolio) {
  const summary = portfolio.summary || {};
  const totalValue = summary.total_value || 0;
  const totalPositions = summary.total_positions || 0;
  const totalPnl = summary.total_pnl || 0;

  updateText('#user-portfolio-value', formatCurrency(totalValue));
  updateText('#user-portfolio-status', `${totalPositions} active position${totalPositions === 1 ? '' : 's'}`);

  const pnlElement = document.getElementById('user-total-pnl');
  if (pnlElement) {
    const isPositive = totalPnl >= 0;
    pnlElement.textContent = `${isPositive ? '+' : ''}${formatCurrency(Math.abs(totalPnl))}`;
    pnlElement.style.color = isPositive ? 'var(--success)' : 'var(--danger)';
  }

  const riskLevelElement = document.getElementById('user-risk-level');
  if (riskLevelElement) {
    let riskLevel = 'LOW';
    let riskClass = 'status-success';
    if (totalPositions > 5) {
      riskLevel = 'MEDIUM';
      riskClass = 'status-warning';
    }
    if (totalPositions > 10) {
      riskLevel = 'HIGH';
      riskClass = 'status-danger';
    }
    riskLevelElement.textContent = riskLevel;
    riskLevelElement.className = `status-indicator ${riskClass}`;
  }

  updateText('#user-risk-details', `${totalPositions} position${totalPositions === 1 ? '' : 's'} open`);
}

function updateUserTradesTable(trades) {
  const tbody = document.getElementById('user-recent-trades');
  if (!tbody) return;
  if (!trades || trades.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-secondary);">No recent trades</td></tr>';
    return;
  }
  tbody.innerHTML = '';
  trades.slice(0, 10).forEach((trade) => {
    const row = document.createElement('tr');
    const timestamp = new Date((trade.timestamp || 0) * 1000);
    const dateString = timestamp.toLocaleDateString('en-US');
    const pnl = trade.pnl || 0;
    row.innerHTML = `
      <td>${dateString}</td>
      <td>${trade.symbol || 'N/A'}</td>
      <td>${trade.side || 'N/A'}</td>
      <td>${trade.quantity || 0}</td>
      <td>$${(trade.price || 0).toFixed(4)}</td>
      <td class="${pnl >= 0 ? 'text-success' : 'text-danger'}">${pnl >= 0 ? '+' : '-'}$${Math.abs(pnl).toFixed(2)}</td>
      <td><span class="status-indicator status-${trade.status === 'closed' ? 'success' : 'warning'}">${trade.status || 'unknown'}</span></td>
    `;
    tbody.appendChild(row);
  });
}

function updateText(selector, text) {
  const element = document.querySelector(selector);
  if (element) {
    element.textContent = text;
  }
}

function formatCurrency(value) {
  return `$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export async function logout() {
  try {
    const response = await fetch('/logout', {
      method: 'GET',
      credentials: 'same-origin',
    });
    if (response.redirected) {
      window.location.href = response.url;
    } else {
      window.location.href = '/login';
    }
  } catch (error) {
    console.error('Logout error:', error);
    window.location.href = '/login';
  }
}

if (typeof window !== 'undefined') {
  window.logout = logout;
}
