import { fetchJson } from '../utils/network.js';

const TABLE_ID = 'market-data-table';
const MAX_SYMBOLS = 20;

function formatPercent(value = 0) {
  return `${value.toFixed(2)}%`;
}

function getSignalClass(confidence = 0) {
  if (confidence >= 0.7) return 'status-success';
  if (confidence >= 0.5) return 'status-warning';
  return 'status-neutral';
}

export async function refreshMarketData() {
  try {
    const data = await fetchJson('/api/market_data');
    const rows = document.getElementById(TABLE_ID);
    if (!rows) return;

    const marketData = data?.market_data || {};
    const aiSignals = data?.ai_signals || {};
    const symbols = Object.keys(marketData).slice(0, MAX_SYMBOLS);

    rows.innerHTML = '';
    symbols.forEach((symbol) => {
  const info = marketData[symbol] || {};
  const signal = aiSignals[symbol] || {};
  const priceChange = info.price_change_24h || 0;
  const volume = Number(info.volume_24h || 0);
      const confidence = signal.confidence || 0;
      const row = document.createElement('tr');
      row.innerHTML = `
        <td>${symbol}</td>
        <td>$${(info.price || 0).toFixed(4)}</td>
        <td class="${priceChange >= 0 ? 'text-success' : 'text-danger'}">${formatPercent(priceChange)}</td>
  <td>${volume.toLocaleString()}</td>
        <td><span class="status-indicator ${getSignalClass(confidence)}">${signal.signal || 'HOLD'}</span></td>
        <td>${formatPercent(confidence * 100)}</td>
        <td>
          <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 12px;" onclick="viewSymbolDetails('${symbol}')">View</button>
        </td>
      `;
      rows.appendChild(row);
    });
  } catch (error) {
    console.error('Error refreshing market data:', error);
  }
}

export function viewSymbolDetails(symbol) {
  const event = new CustomEvent('dashboard:view-symbol', { detail: { symbol }, cancelable: true });
  const handled = window.dispatchEvent(event);
  if (handled) {
    alert(`Symbol details for ${symbol} coming soon.`);
  }
}

function handleNavigation(event) {
  if (event.target.closest('[data-page="market-data"]')) {
    setTimeout(() => {
      refreshMarketData();
    }, 100);
  }
}

document.addEventListener('click', handleNavigation);

document.addEventListener('DOMContentLoaded', () => {
  const section = document.getElementById('market-data');
  if (section && section.classList.contains('active')) {
    refreshMarketData();
  }
});

if (typeof window !== 'undefined') {
  window.refreshMarketData = refreshMarketData;
  window.viewSymbolDetails = viewSymbolDetails;
}
