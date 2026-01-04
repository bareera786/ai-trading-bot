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

  setResultsMessage(resultsEl, 'muted', 'Running backtest...');

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
    setResultsMessage(resultsEl, 'danger', `Error: ${error?.message || 'Backtest failed'}`);
  }
}

function setResultsMessage(resultsEl, kind, message) {
  if (!resultsEl) return;
  resultsEl.textContent = '';
  const p = document.createElement('p');
  if (kind === 'danger') p.className = 'text-danger';
  else if (kind === 'success') p.className = 'text-success';
  else p.className = 'text-muted';
  p.textContent = message;
  resultsEl.appendChild(p);
}

function displayResults(results) {
  const resultsEl = document.getElementById(IDS.results);
  if (!resultsEl) return;

  if (!results || !Array.isArray(results)) {
    setResultsMessage(resultsEl, 'muted', 'No results available');
    return;
  }

  resultsEl.textContent = '';
  const container = document.createElement('div');
  container.className = 'data-table-container';

  const table = document.createElement('table');
  table.className = 'data-table';

  const thead = document.createElement('thead');
  const headRow = document.createElement('tr');
  const thMetric = document.createElement('th');
  thMetric.textContent = 'Metric';
  const thValue = document.createElement('th');
  thValue.textContent = 'Value';
  headRow.appendChild(thMetric);
  headRow.appendChild(thValue);
  thead.appendChild(headRow);

  const tbody = document.createElement('tbody');
  results.forEach((result) => {
    const row = document.createElement('tr');
    const tdMetric = document.createElement('td');
    const tdValue = document.createElement('td');
    tdMetric.textContent = result?.metric != null ? String(result.metric) : '';
    tdValue.textContent = result?.value != null ? String(result.value) : '';
    row.appendChild(tdMetric);
    row.appendChild(tdValue);
    tbody.appendChild(row);
  });

  table.appendChild(thead);
  table.appendChild(tbody);
  container.appendChild(table);
  resultsEl.appendChild(container);
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
        const custom = data.custom_symbols
          .map((s) => (s != null ? String(s).trim() : ''))
          .filter((s) => s && !options.includes(s));
        options = options.concat(custom);
      }
    }
  } catch (e) { /* ignore */ }

  select.textContent = '';
  const frag = document.createDocumentFragment();
  options.forEach((sym) => {
    const opt = document.createElement('option');
    opt.value = sym;
    opt.textContent = sym;
    frag.appendChild(opt);
  });
  select.appendChild(frag);
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