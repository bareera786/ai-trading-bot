// --- Admin Symbol Management Backtest Integration ---
function showBacktestModal(symbol) {
  document.getElementById('symbol-backtest-modal').style.display = 'flex';
  document.getElementById('backtest-modal-symbol').textContent = symbol;
  document.getElementById('symbol-backtest-results').innerHTML = '';
  document.getElementById('symbol-backtest-form').onsubmit = async function() {
    const dateRange = document.getElementById('backtest-date-range').value.trim() || '2024-01-01 to 2024-12-31';
    const strategy = document.getElementById('backtest-strategy').value || 'Ultimate Ensemble';
    const resultsEl = document.getElementById('symbol-backtest-results');
    resultsEl.innerHTML = '<p style="color: var(--text-secondary);">Running backtest...</p>';
    try {
      const response = await fetch('/api/backtest/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({ symbol, date_range: dateRange, strategy }),
      });
      const data = await response.json();
      if (!response.ok || data.error) throw new Error(data.error || 'Backtest failed');
      let html = '<table class="data-table"><thead><tr><th>Metric</th><th>Value</th></tr></thead><tbody>';
      (data.results || []).forEach(result => {
        html += `<tr><td>${result.metric}</td><td>${result.value}</td></tr>`;
      });
      html += '</tbody></table>';
      resultsEl.innerHTML = html;
    } catch (error) {
      resultsEl.innerHTML = `<p style="color: #e74c3c;">Error: ${error.message}</p>`;
    }
    return false;
  };
}

// --- Patch for admin symbol table rendering ---
if (typeof window !== 'undefined') {
  window.showBacktestModal = showBacktestModal;
}
import { fetchJson } from '../utils/network.js';

const state = {
  symbols: [],
  isPremium: false,
};

function setStatus(message, tone = 'neutral') {
  const el = document.getElementById('custom-symbol-status');
  if (!el) return;
  el.textContent = message;
  el.className = `status-pill status-${tone}`;
}

function renderSymbols() {
  const list = document.getElementById('custom-symbols-list');
  if (!list) return;
  list.innerHTML = '';

  if (!state.symbols.length) {
    const empty = document.createElement('div');
    empty.className = 'empty-hint';
    empty.textContent = 'No custom symbols yet. Add USDT pairs to train & auto-trade.';
    list.appendChild(empty);
    return;
  }

  state.symbols.forEach((symbol) => {
    const pill = document.createElement('div');
    pill.className = 'symbol-pill';
    pill.innerHTML = `
      <span>${symbol}</span>
      <button aria-label="Remove" class="icon-btn" data-symbol="${symbol}">✕</button>
    `;
    pill.querySelector('button').addEventListener('click', () => removeSymbol(symbol));
    list.appendChild(pill);
  });
}

function addSymbol() {
  const input = document.getElementById('custom-symbol-input');
  if (!input) return;
  const raw = input.value.trim().toUpperCase();
  if (!raw) return;
  if (!raw.endsWith('USDT') || raw.length <= 4) {
    setStatus('Symbols must end with USDT (e.g., ARBUSDT).', 'warning');
    return;
  }
  if (state.symbols.includes(raw)) {
    setStatus('Symbol already added.', 'warning');
    return;
  }
  state.symbols.push(raw);
  input.value = '';
  renderSymbols();
  setStatus(`${raw} added. Save to persist.`, 'success');
}

function removeSymbol(symbol) {
  state.symbols = state.symbols.filter((s) => s !== symbol);
  renderSymbols();
  setStatus(`${symbol} removed. Save to persist.`, 'neutral');
}

async function saveSymbols() {
  const user = await fetchJson('/api/current_user');
  const isAdmin = !!user?.is_admin;
  if (!state.isPremium && !isAdmin) return;
  try {
    const res = await fetch('/api/user/custom_symbols', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ symbols: state.symbols }),
    });
    const data = await res.json();
    if (!res.ok || data.error) {
      setStatus(data.error || 'Failed to save symbols.', 'danger');
      return;
    }
    state.symbols = data.custom_symbols || [];
    renderSymbols();
    setStatus('Custom symbols saved.', 'success');
  } catch (error) {
    console.error('Failed to save custom symbols', error);
    setStatus('Failed to save symbols. Please retry.', 'danger');
  }
}

async function loadCustomSymbols() {
  const gate = document.getElementById('premium-guard');
  const content = document.getElementById('premium-symbols-content');

  try {
    const user = await fetchJson('/api/current_user');
    state.isPremium = !!user?.is_premium;
    const isAdmin = !!user?.is_admin; // Check if user is admin
    if (!state.isPremium && !isAdmin) {
      if (gate) gate.style.display = 'flex';
      if (content) content.style.display = 'none';
      setStatus('Premium required for custom symbols.', 'warning');
      return;
    }
    if (gate) gate.style.display = 'none';
    if (content) content.style.display = 'block';

    const data = await fetchJson('/api/user/custom_symbols');
    if (data?.custom_symbols && Array.isArray(data.custom_symbols)) {
      state.symbols = data.custom_symbols;
      renderSymbols();
      setStatus('Loaded your custom symbols.', 'success');
    } else {
      state.symbols = [];
      renderSymbols();
      setStatus('No custom symbols yet. Add some below.', 'neutral');
    }
  } catch (error) {
    console.error('Failed to load custom symbols', error);
    setStatus('Unable to load symbols. Please refresh.', 'danger');
  }
}

function bindEvents() {
  const addBtn = document.getElementById('custom-symbol-add');
  const saveBtn = document.getElementById('custom-symbol-save');
  const input = document.getElementById('custom-symbol-input');

  if (addBtn) addBtn.addEventListener('click', addSymbol);
  if (saveBtn) saveBtn.addEventListener('click', saveSymbols);
  if (input) {
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        addSymbol();
      }
    });
  }
}

function init() {
  bindEvents();
  loadCustomSymbols();
}

if (typeof window !== 'undefined') {
  window.addEventListener('dashboard:symbol-management-visible', init, { once: true });
  document.addEventListener('DOMContentLoaded', () => {
    const section = document.getElementById('symbol-management');
    if (section && section.classList.contains('active')) {
      init();
    }
  });
}

export { init as initSymbolsPage };
