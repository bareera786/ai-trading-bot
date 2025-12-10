import { fetchJson } from '../utils/network.js';

const IDS = {
  symbol: 'backtest-symbol',
  dateRange: 'backtest-date-range',
  strategy: 'backtest-strategy',
  results: 'backtest-results',
  runButton: 'run-backtest-btn',
};

async function runBacktest() {
  const symbolSelect = document.getElementById(IDS.symbol);
  const symbol = symbolSelect?.value || 'BTCUSDT';
  const dateRange = document.getElementById(IDS.dateRange)?.value.trim() || '2024-01-01 to 2024-12-31';
  const strategy = document.getElementById(IDS.strategy)?.value || 'Ultimate Ensemble';

  const resultsEl = document.getElementById(IDS.results);
  if (!resultsEl) return;

  resultsEl.innerHTML = '<p style="color: var(--text-secondary);">Running backtest...</p>';

  try {
    const response = await fetch('/api/backtest/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ symbol, date_range: dateRange, strategy }),
    });
    const data = await response.json();
    if (!response.ok || data.error) {
      throw new Error(data.error || 'Backtest failed');
    }
    displayResults(data.results);
  } catch (error) {
    console.error('Backtest error:', error);
    resultsEl.innerHTML = `<p style="color: #e74c3c;">Error: ${error.message}</p>`;
  }
}

function displayResults(results) {
  const resultsEl = document.getElementById(IDS.results);
  if (!resultsEl) return;

  if (!results || !Array.isArray(results)) {
    resultsEl.innerHTML = '<p style="color: var(--text-secondary);">No results available</p>';
    return;
  }

  let html = '<table class="data-table"><thead><tr><th>Metric</th><th>Value</th></tr></thead><tbody>';
  results.forEach(result => {
    html += `<tr><td>${result.metric}</td><td>${result.value}</td></tr>`;
  });
  html += '</tbody></table>';
  resultsEl.innerHTML = html;
}

async function populateBacktestSymbols() {
  const select = document.getElementById(IDS.symbol);
  if (!select) return;
  // Default symbol
  let options = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT", "SOLUSDT", "DOTUSDT", "DOGEUSDT", "AVAXUSDT", "MATICUSDT", "LINKUSDT", "LTCUSDT", "BCHUSDT", "XLMUSDT", "ETCUSDT"];
  try {
    const user = await fetchJson('/api/current_user');
    if (user?.is_premium) {
      const data = await fetchJson('/api/user/custom_symbols');
      if (data?.custom_symbols && Array.isArray(data.custom_symbols)) {
        options = options.concat(data.custom_symbols.filter(s => !options.includes(s)));
      }
    }
  } catch (e) { /* ignore */ }
  select.innerHTML = options.map(s => `<option value="${s}">${s}</option>`).join('');
}

if (typeof window !== 'undefined') {
  window.addEventListener('dashboard:backtest-lab-visible', () => {
    populateBacktestSymbols();
  });
  document.addEventListener('DOMContentLoaded', () => {
    const section = document.getElementById('backtest-lab');
    if (section && section.classList.contains('active')) {
      populateBacktestSymbols();
    }
  });

  Object.assign(window, {
    runBacktest,
  });
}