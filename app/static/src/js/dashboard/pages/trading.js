import { fetchJson } from '../utils/network.js';

function getInputValue(id) {
  return document.getElementById(id)?.value?.trim();
}

export async function executeSpotTrade() {
  const symbol = getInputValue('spot-trade-symbol');
  const side = document.getElementById('spot-trade-side')?.value || 'buy';
  const amount = getInputValue('spot-trade-amount');

  if (!symbol || !amount) {
    alert('Please fill in all fields');
    return;
  }

  try {
    const response = await fetch('/api/spot/trade', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ symbol, side, amount: parseFloat(amount) }),
    });
    const data = await response.json();
    if (data.error) {
      alert(`Error: ${data.error}`);
    } else {
      alert('Spot trade executed successfully!');
      refreshSpotData();
    }
  } catch (error) {
    console.error('Failed to execute spot trade:', error);
    alert('Failed to execute trade');
  }
}

export async function toggleSpotTrading() {
  try {
    const data = await fetchJson('/api/spot/toggle', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    alert(data.message || 'Spot trading updated');
    // Update button text based on new state
    updateSpotTradingButton(data.trading_enabled);
  } catch (error) {
    console.error('Failed to toggle spot trading:', error);
    alert('Failed to toggle spot trading');
  }
}

function updateSpotTradingButton(enabled) {
  const button = document.getElementById('spot-toggle-btn');
  if (button) {
    button.textContent = enabled ? 'Disable Spot Trading' : 'Enable Spot Trading';
    button.className = enabled ? 'btn btn-danger' : 'btn btn-secondary';
  }
}

export async function executeFuturesTrade() {
  const symbol = getInputValue('futures-trade-symbol');
  const side = document.getElementById('futures-trade-side')?.value || 'buy';
  const quantity = getInputValue('futures-trade-quantity');
  const leverage = parseInt(getInputValue('futures-trade-leverage') || '3', 10);

  if (!symbol || !quantity) {
    alert('Please fill in symbol and quantity');
    return;
  }

  try {
    const response = await fetch('/api/futures/trade', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ symbol, side, quantity: parseFloat(quantity), leverage }),
    });
    const data = await response.json();
    if (data.error) {
      alert(`Error: ${data.error}`);
    } else {
      alert('Futures trade executed successfully!');
      refreshFuturesData();
    }
  } catch (error) {
    console.error('Failed to execute futures trade:', error);
    alert('Failed to execute futures trade');
  }
}

export async function toggleFuturesTrading(forceEnable = null) {
  const button = document.getElementById('futures-toggle-btn');
  try {
    // Query current state so we can toggle when enable is omitted
    const dashboard = await fetchJson('/api/dashboard');
    const current = !!(dashboard && dashboard.system_status && dashboard.system_status.futures_trading_enabled);
    const enable = forceEnable === null ? !current : !!forceEnable;

    // Show spinner and disable button while request is in-flight
    if (button) {
      button.disabled = true;
      button.dataset._origText = button.textContent;
      button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
    }

    const data = await fetchJson('/api/futures/toggle', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enable }),
    });

    alert(data.message || 'Futures trading updated');
    updateFuturesTradingButton(data.futures_trading_enabled);
  } catch (error) {
    console.error('Failed to toggle futures trading:', error);
    alert('Failed to toggle futures trading');
  } finally {
    if (button) {
      button.disabled = false;
      // restore text and ensure state sync
      if (button.dataset._origText) {
        button.textContent = button.dataset._origText;
        delete button.dataset._origText;
      }
      // refresh from server to sync the UI state
      try {
        await refreshFuturesData();
      } catch (err) {
        // best-effort only
      }
    }
  }
}

function updateFuturesTradingButton(enabled) {
  const button = document.getElementById('futures-toggle-btn');
  if (button) {
    button.textContent = enabled ? 'Disable Futures' : 'Enable Futures';
    button.className = enabled ? 'btn btn-danger' : 'btn btn-secondary';
  }
}

function updateFuturesPositionsTable(positions) {
  const tbody = document.getElementById('futures-positions');
  if (!tbody) return;

  tbody.innerHTML = '';

  if (!positions || Object.keys(positions).length === 0) {
    const row = document.createElement('tr');
    row.innerHTML = '<td colspan="6" style="text-align: center; padding: 2rem; color: var(--text-secondary);">No open futures positions</td>';
    tbody.appendChild(row);
    return;
  }

  Object.entries(positions).forEach(([symbol, position]) => {
    const row = document.createElement('tr');
    const pnl = position.unrealized_pnl || 0;
    const pnlClass = pnl >= 0 ? 'text-success' : 'text-danger';
    const pnlText = pnl >= 0 ? `+$${pnl.toFixed(2)}` : `-$${Math.abs(pnl).toFixed(2)}`;

    row.innerHTML = `
      <td>${symbol}</td>
      <td>${position.side || 'N/A'}</td>
      <td>${position.size || 0}</td>
      <td>$${(position.entry_price || 0).toFixed(4)}</td>
      <td class="${pnlClass}">${pnlText}</td>
      <td>${position.leverage || 1}x</td>
    `;
    tbody.appendChild(row);
  });
}

export async function refreshSpotData() {
  try {
    const dashboard = await fetchJson('/api/dashboard');
    if (dashboard && dashboard.system_status) {
      updateSpotTradingButton(dashboard.system_status.trading_enabled);
    }

    // Fetch portfolio data for spot trading display
    const portfolio = await fetchJson('/api/portfolio');
    if (portfolio && portfolio.ultimate) {
      updateSpotPortfolioDisplay(portfolio.ultimate, dashboard.system_status.trading_enabled);
    }

    console.log('Spot trading data refreshed');
  } catch (error) {
    console.error('Failed to refresh spot data:', error);
  }
}

function updateSpotPortfolioDisplay(portfolioData, tradingEnabled) {
  // Update spot balance card
  const balanceElement = document.querySelector('#spot .dashboard-card:nth-child(1) .card-value');
  if (balanceElement) {
    balanceElement.textContent = `$${portfolioData.available_balance.toFixed(2)}`;
  }

  // Update open positions count
  const positionsCountElement = document.querySelector('#spot .dashboard-card:nth-child(2) .card-value');
  if (positionsCountElement) {
    const positionsCount = Object.keys(portfolioData.open_positions || {}).length;
    positionsCountElement.textContent = positionsCount;
  }

  // Update today's P&L
  const pnlElement = document.querySelector('#spot .dashboard-card:nth-child(3) .card-value');
  if (pnlElement) {
    const pnl = portfolioData.total_pnl || 0;
    const isPositive = pnl >= 0;
    pnlElement.textContent = `${isPositive ? '+' : ''}$${Math.abs(pnl).toFixed(2)}`;
    pnlElement.style.color = isPositive ? 'var(--success)' : 'var(--danger)';
  }

  // Update trading status
  const statusElement = document.querySelector('#spot .dashboard-card:nth-child(4) .card-value .status-indicator');
  if (statusElement) {
    statusElement.className = `status-indicator ${tradingEnabled ? 'status-success' : 'status-warning'}`;
    statusElement.textContent = tradingEnabled ? 'ACTIVE' : 'INACTIVE';
  }

  // Update positions table
  const positionsTable = document.getElementById('spot-positions');
  if (positionsTable) {
    positionsTable.innerHTML = '';
    const positions = portfolioData.open_positions || {};

    if (Object.keys(positions).length === 0) {
      const emptyRow = document.createElement('tr');
      emptyRow.innerHTML = '<td colspan="8" style="text-align: center; padding: var(--spacing-lg);">No open positions</td>';
      positionsTable.appendChild(emptyRow);
    } else {
      Object.entries(positions).forEach(([symbol, position]) => {
        const row = document.createElement('tr');
        const currentPrice = position.current_price || position.avg_price || 0;
        const pnl = position.pnl || 0;
        const pnlPercent = position.pnl_percent || 0;

        row.innerHTML = `
          <td>${symbol}</td>
          <td>${position.side || 'N/A'}</td>
          <td>${position.quantity || 0}</td>
          <td>$${position.avg_price ? position.avg_price.toFixed(2) : '0.00'}</td>
          <td>$${currentPrice.toFixed(2)}</td>
          <td style="color: ${pnl >= 0 ? 'var(--success)' : 'var(--danger)'}">${pnl >= 0 ? '+' : ''}$${Math.abs(pnl).toFixed(2)}</td>
          <td style="color: ${pnlPercent >= 0 ? 'var(--success)' : 'var(--danger)'}">${pnlPercent >= 0 ? '+' : ''}${pnlPercent.toFixed(2)}%</td>
          <td><button class="btn btn-sm btn-danger" onclick="closeSpotPosition('${symbol}')">Close</button></td>
        `;
        positionsTable.appendChild(row);
      });
    }
  }
}

export async function closeSpotPosition(symbol) {
  alert(`Close position feature for ${symbol} is not yet implemented. Please use manual trading to close positions.`);
}

export async function refreshFuturesData() {
  try {
    const dashboard = await fetchJson('/api/dashboard');
    if (dashboard && dashboard.system_status) {
      updateFuturesTradingButton(dashboard.system_status.futures_trading_enabled);
    }

    // Fetch futures data including positions
    const futuresData = await fetchJson('/api/futures');
    if (futuresData && futuresData.positions) {
      updateFuturesPositionsTable(futuresData.positions);
    }
    console.log('Futures trading data refreshed');
  } catch (error) {
    console.error('Failed to refresh futures data:', error);
  }
}

if (typeof window !== 'undefined') {
  window.addEventListener('dashboard:spot-visible', () => {
    refreshSpotData();
  });

  window.addEventListener('dashboard:futures-visible', () => {
    refreshFuturesData();
  });

  document.addEventListener('DOMContentLoaded', () => {
    // Wire up button event listeners (replaces inline onclick handlers)
    document.getElementById('execute-spot-trade-btn')?.addEventListener('click', executeSpotTrade);
    document.getElementById('toggle-spot-trading-btn')?.addEventListener('click', toggleSpotTrading);
    document.getElementById('execute-futures-trade-btn')?.addEventListener('click', executeFuturesTrade);
    document.getElementById('futures-toggle-btn')?.addEventListener('click', toggleFuturesTrading);
  });

  Object.assign(window, {
    executeSpotTrade,
    toggleSpotTrading,
    executeFuturesTrade,
    toggleFuturesTrading,
    refreshSpotData,
    refreshFuturesData,
    closeSpotPosition,
  });
}
