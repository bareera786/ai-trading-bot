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
  systemSymbols: [],
  systemLoading: false,
};

function formatMaybeDate(value, { dateOnly = false } = {}) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return dateOnly ? date.toLocaleDateString() : date.toLocaleString();
}

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

function setSystemTableState(message) {
  const tbody = document.getElementById('symbols-table');
  if (!tbody) return;
  tbody.innerHTML = `<tr><td colspan="5" class="text-muted" style="text-align:center;padding:var(--spacing-2xl);">${message}</td></tr>`;
}

function renderModelReadyCell(row, symbolRow) {
  const td = document.createElement('td');

  const uReady = !!symbolRow.ultimate_model_ready;
  const oReady = !!symbolRow.optimized_model_ready;

  const badge = document.createElement('span');
  badge.className = `status-indicator ${uReady && oReady ? 'status-success' : (uReady || oReady ? 'status-warning' : 'status-neutral')}`;
  badge.textContent = uReady && oReady ? 'READY' : (uReady || oReady ? 'PARTIAL' : 'NOT READY');
  td.appendChild(badge);

  const meta = document.createElement('div');
  meta.className = 'text-muted';
  meta.style.marginTop = '6px';
  meta.style.fontSize = 'var(--font-size-xs)';
  meta.textContent = `Ultimate: ${uReady ? 'Yes' : 'No'} • Optimized: ${oReady ? 'Yes' : 'No'}`;
  td.appendChild(meta);

  row.appendChild(td);
}

function renderLastTrainedCell(row, symbolRow) {
  const td = document.createElement('td');
  td.innerHTML = `
    <div>Ultimate: ${formatMaybeDate(symbolRow.ultimate_last_trained, { dateOnly: true })}</div>
    <div class="text-muted" style="margin-top: 4px; font-size: var(--font-size-xs);">Optimized: ${formatMaybeDate(symbolRow.optimized_last_trained, { dateOnly: true })}</div>
  `;
  row.appendChild(td);
}

async function setSymbolEnabled(symbol, enabled) {
  const endpoint = enabled ? '/api/symbols/enable' : '/api/symbols/disable';
  const res = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
    body: JSON.stringify({ symbol }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.error) {
    throw new Error(data.error || 'Request failed');
  }
  return data;
}

function renderSystemSymbolsTable(symbols) {
  const tbody = document.getElementById('symbols-table');
  if (!tbody) return;

  tbody.innerHTML = '';

  if (!symbols.length) {
    setSystemTableState('No symbols found.');
    return;
  }

  symbols.forEach((symbolRow) => {
    const row = document.createElement('tr');

    const symbolCell = document.createElement('td');
    symbolCell.textContent = symbolRow.symbol || '';
    row.appendChild(symbolCell);

    const statusCell = document.createElement('td');
    const isDisabled = !!symbolRow.disabled;
    const isActive = !!symbolRow.active && !isDisabled;
    const statusBadge = document.createElement('span');
    statusBadge.className = `status-indicator ${isDisabled ? 'status-danger' : (isActive ? 'status-success' : 'status-neutral')}`;
    statusBadge.textContent = isDisabled ? 'DISABLED' : (isActive ? 'ACTIVE' : 'INACTIVE');
    statusCell.appendChild(statusBadge);
    row.appendChild(statusCell);

    renderModelReadyCell(row, symbolRow);
    renderLastTrainedCell(row, symbolRow);

    const actionsCell = document.createElement('td');
    actionsCell.className = 'symbols-col-actions';

    const makeBtn = (label, className, onClick) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = `btn btn-sm ${className}`;
      btn.textContent = label;
      btn.addEventListener('click', onClick);
      return btn;
    };

    const symbol = symbolRow.symbol;
    actionsCell.appendChild(
      makeBtn(isDisabled ? 'Enable' : 'Disable', isDisabled ? 'btn-primary' : 'btn-warning', async () => {
        try {
          actionsCell.querySelectorAll('button').forEach((b) => (b.disabled = true));
          await setSymbolEnabled(symbol, isDisabled);
          await loadSystemSymbols();
        } catch (error) {
          console.error('Failed to toggle symbol', error);
          alert(`Failed to update ${symbol}: ${error.message}`);
        } finally {
          actionsCell.querySelectorAll('button').forEach((b) => (b.disabled = false));
        }
      })
    );

    actionsCell.appendChild(
      makeBtn('Backtest', 'btn-secondary', () => showBacktestModal(symbol))
    );

    row.appendChild(actionsCell);
    tbody.appendChild(row);
  });
}

async function loadSystemSymbols() {
  if (state.systemLoading) return;
  state.systemLoading = true;

  try {
    const search = document.getElementById('symbol-search')?.value?.trim() || '';
    const status = document.getElementById('symbol-status-filter')?.value || '';

    setSystemTableState('Loading symbols...');

    const url = `/api/symbols?page=1&page_size=100&search=${encodeURIComponent(search)}`;
    const data = await fetchJson(url);

    let symbols = Array.isArray(data?.symbols) ? data.symbols : [];
    if (status === 'active') {
      symbols = symbols.filter((s) => !!s.active && !s.disabled);
    } else if (status === 'disabled') {
      symbols = symbols.filter((s) => !!s.disabled);
    }

    state.systemSymbols = symbols;
    renderSystemSymbolsTable(symbols);
  } catch (error) {
    console.error('Failed to load symbols', error);
    setSystemTableState('Failed to load symbols.');
  } finally {
    state.systemLoading = false;
  }
}

function bindSystemSymbolsEvents() {
  const search = document.getElementById('symbol-search');
  const filter = document.getElementById('symbol-status-filter');
  if (search && search.dataset.bound !== '1') {
    search.dataset.bound = '1';
    let t;
    search.addEventListener('input', () => {
      clearTimeout(t);
      t = setTimeout(loadSystemSymbols, 200);
    });
  }
  if (filter && filter.dataset.bound !== '1') {
    filter.dataset.bound = '1';
    filter.addEventListener('change', loadSystemSymbols);
  }
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

  if (addBtn && addBtn.dataset.bound !== '1') {
    addBtn.dataset.bound = '1';
    addBtn.addEventListener('click', addSymbol);
  }
  if (saveBtn && saveBtn.dataset.bound !== '1') {
    saveBtn.dataset.bound = '1';
    saveBtn.addEventListener('click', saveSymbols);
  }
  if (input) {
    if (input.dataset.bound !== '1') {
      input.dataset.bound = '1';
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        addSymbol();
      }
    });
    }
  }
}

function init() {
  bindEvents();
  bindSystemSymbolsEvents();
  loadCustomSymbols();
  loadSystemSymbols();
}

if (typeof window !== 'undefined') {
  window.addEventListener('dashboard:symbols-visible', init);
  document.addEventListener('DOMContentLoaded', () => {
    const section = document.getElementById('symbols');
    if (section && section.classList.contains('active')) {
      init();
    }
  });
}

export { init as initSymbolsPage };
