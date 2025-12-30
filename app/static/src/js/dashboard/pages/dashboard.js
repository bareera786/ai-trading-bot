import { fetchJson } from '../utils/network.js';

let performanceChart = null;

export async function refreshDashboardCards() {
  try {
    const data = await fetchJson('/api/status');
    
    // Update portfolio value
    const portfolioCard = document.querySelector('#dashboard .dashboard-card:nth-child(1) .card-value');
    if (portfolioCard) {
      if (data && data.portfolio) {
        const totalValue = (data.portfolio.total_balance || 0) + (data.portfolio.unrealized_pnl || 0);
        portfolioCard.textContent = formatCurrency(totalValue);
        
        const portfolioChange = document.getElementById('portfolio-change');
        if (portfolioChange) {
          const changePercent = data.portfolio.daily_change_percent || 0;
          portfolioChange.textContent = `${changePercent >= 0 ? '+' : ''}${changePercent.toFixed(1)}% today`;
          portfolioChange.style.color = changePercent >= 0 ? 'var(--success)' : 'var(--danger)';
        }
      } else {
        portfolioCard.textContent = '$0.00';
        const portfolioChange = document.getElementById('portfolio-change');
        if (portfolioChange) portfolioChange.textContent = 'No data available';
      }
    }

    // Update active trades
    const tradesCard = document.querySelector('#dashboard .dashboard-card:nth-child(2) .card-value');
    if (tradesCard) {
      if (data && data.portfolio) {
        const openPositions = Object.keys(data.portfolio.open_positions || {}).length;
        tradesCard.textContent = openPositions;
        
        const tradesSubtitle = document.getElementById('trades-subtitle');
        if (tradesSubtitle) {
          tradesSubtitle.textContent = openPositions > 0 ? `${openPositions} active positions` : 'No active positions';
        }
      } else {
        tradesCard.textContent = '0';
        const tradesSubtitle = document.getElementById('trades-subtitle');
        if (tradesSubtitle) tradesSubtitle.textContent = 'No active positions';
      }
    }

    // Update win rate
    const winRateCard = document.querySelector('#dashboard .dashboard-card:nth-child(3) .card-value');
    if (winRateCard) {
      if (data && data.performance) {
        const winRate = data.performance.win_rate || 0;
        winRateCard.textContent = `${(winRate * 100).toFixed(1)}%`;
        
        const winRatePeriod = document.getElementById('win-rate-period');
        if (winRatePeriod) winRatePeriod.textContent = 'Last 30 days';
      } else {
        winRateCard.textContent = '0.0%';
        const winRatePeriod = document.getElementById('win-rate-period');
        if (winRatePeriod) winRatePeriod.textContent = 'No trading history';
      }
    }

    // Update system status
    const systemCard = document.getElementById('system-status-indicator');
    if (systemCard) {
      if (data && data.system_status) {
        const isOnline = data.system_status.trading_enabled && data.system_status.models_loaded;
        systemCard.className = `status-indicator ${isOnline ? 'status-success' : 'status-warning'}`;
        systemCard.textContent = isOnline ? 'ONLINE' : 'OFFLINE';
      } else {
        systemCard.className = 'status-indicator status-warning';
        systemCard.textContent = 'UNKNOWN';
      }
    }

    await loadUserDashboardData();
    await updatePerformanceChart();
  } catch (error) {
    console.error('Failed to refresh dashboard cards:', error);
    // Set fallback values
    const portfolioCard = document.querySelector('#dashboard .dashboard-card:nth-child(1) .card-value');
    if (portfolioCard) portfolioCard.textContent = '$0.00';
    
    const tradesCard = document.querySelector('#dashboard .dashboard-card:nth-child(2) .card-value');
    if (tradesCard) tradesCard.textContent = '0';
    
    const winRateCard = document.querySelector('#dashboard .dashboard-card:nth-child(3) .card-value');
    if (winRateCard) winRateCard.textContent = '0.0%';
    
    const systemCard = document.getElementById('system-status-indicator');
    if (systemCard) {
      systemCard.className = 'status-indicator status-error';
      systemCard.textContent = 'ERROR';
    }
  }
}

async function updatePerformanceChart() {
  if (typeof Chart === 'undefined') return;

  const ctx = document.getElementById('performance-chart');
  if (!ctx) return;

  // Fetch performance data
  const data = await fetchJson('/api/performance_chart');
  const chartData = data ? data.chart_data : {};
  const labels = chartData.labels || ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];
  const values = chartData.values || [10000, 10500, 10200, 10800, 10600, 11000];

  if (!performanceChart) {
    performanceChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: 'Portfolio Value',
          data: values,
          borderColor: 'var(--primary)',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          tension: 0.4,
          fill: true
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: {
            display: false
          }
        },
        scales: {
          y: {
            beginAtZero: false,
            ticks: {
              callback: function(value) {
                return '$' + value.toLocaleString();
              }
            }
          }
        }
      }
    });
  } else {
    performanceChart.data.labels = labels;
    performanceChart.data.datasets[0].data = values;
    performanceChart.update();
  }
}

export async function refreshRecentActivity() {
  const user = await fetchJson('/api/current_user');
  const mergeParam = user && user.is_admin ? '&merge_db=1' : '';
  const data = await fetchJson(`/api/trades?page=1&limit=10${mergeParam}`);
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
