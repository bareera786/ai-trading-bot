import { fetchJson } from '../utils/network.js';

const TABLE_ID = 'market-data-table';
const PHASES_BODY_ID = 'phases-table';
const PHASES_HEADER_ID = 'phases-header-row';
const MAX_SYMBOLS = 20;

let phasesPollTimer = null;

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

    // Best-effort: keep phases in sync while market-data is visible.
    if (isMarketDataActive()) {
      await refreshExecutionPhases();
      startPhasesPolling();
    }
  } catch (error) {
    console.error('Error refreshing market data:', error);
  }
}

function isMarketDataActive() {
  const section = document.getElementById('market-data');
  return !!(section && section.classList.contains('active') && !document.hidden);
}

function startPhasesPolling() {
  if (phasesPollTimer) return;
  phasesPollTimer = setInterval(async () => {
    if (!isMarketDataActive()) {
      stopPhasesPolling();
      return;
    }
    try {
      await refreshExecutionPhases();
    } catch (err) {
      // best-effort only
    }
  }, 5000);
}

function stopPhasesPolling() {
  if (!phasesPollTimer) return;
  clearInterval(phasesPollTimer);
  phasesPollTimer = null;
}

function phaseLabel(phase) {
  return String(phase || '').replace(/_/g, ' ');
}

function phaseCellClass(status) {
  const s = String(status || '').toLowerCase();
  if (s === 'ok' || s === 'success') return 'status-success';
  if (s === 'error' || s === 'failed' || s === 'fail') return 'status-danger';
  if (s === 'running' || s === 'in_progress') return 'status-warning';
  return 'status-neutral';
}

function phaseCellText(status) {
  const s = String(status || '').toLowerCase();
  if (s === 'ok' || s === 'success') return 'OK';
  if (s === 'error' || s === 'failed' || s === 'fail') return 'ERR';
  if (s === 'running' || s === 'in_progress') return 'RUN';
  return '-';
}

export async function refreshExecutionPhases() {
  const tbody = document.getElementById(PHASES_BODY_ID);
  const headerRow = document.getElementById(PHASES_HEADER_ID);
  if (!tbody || !headerRow) return;

  try {
    const data = await fetchJson('/api/phases');
    const phaseOrder = Array.isArray(data?.phase_order) ? data.phase_order : [];
    const phasesBySymbol = data?.phases || {};

    // Build header.
    headerRow.innerHTML = '<th>Symbol</th>';
    if (phaseOrder.length) {
      phaseOrder.forEach((phase) => {
        const th = document.createElement('th');
        th.textContent = phaseLabel(phase);
        headerRow.appendChild(th);
      });
    } else {
      const th = document.createElement('th');
      th.textContent = 'Phase';
      headerRow.appendChild(th);
    }

    const symbols = Object.keys(phasesBySymbol || {}).slice(0, MAX_SYMBOLS);
    tbody.innerHTML = '';

    if (!symbols.length) {
      const row = document.createElement('tr');
      row.innerHTML = `<td colspan="${Math.max(2, phaseOrder.length + 1)}" class="text-muted" style="text-align:center;padding:var(--spacing-2xl);">No phase data yet.</td>`;
      tbody.appendChild(row);
      return;
    }

    symbols.forEach((symbol) => {
      const entry = phasesBySymbol[symbol] || {};
      const perPhase = entry.phases || {};

      const row = document.createElement('tr');
      const symCell = document.createElement('td');
      symCell.textContent = symbol;
      row.appendChild(symCell);

      const phasesToRender = phaseOrder.length ? phaseOrder : [entry.current_phase || 'unknown'];
      phasesToRender.forEach((phaseName) => {
        const phaseInfo = perPhase?.[phaseName] || {};
        const status = phaseInfo.status || (entry.current_phase === phaseName ? 'running' : '');
        const progress = phaseInfo.progress;
        const detail = phaseInfo.detail;

        const td = document.createElement('td');
        const badge = document.createElement('span');
        badge.className = `status-indicator ${phaseCellClass(status)}`;
        badge.textContent = phaseCellText(status);
        const titleParts = [];
        if (phaseName) titleParts.push(phaseLabel(phaseName));
        if (typeof progress === 'number') titleParts.push(`Progress: ${progress}%`);
        if (detail) titleParts.push(String(detail));
        if (titleParts.length) badge.title = titleParts.join(' • ');
        td.appendChild(badge);
        row.appendChild(td);
      });

      tbody.appendChild(row);
    });
  } catch (error) {
    console.error('Error refreshing phases:', error);
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
      refreshExecutionPhases();
      startPhasesPolling();
    }, 100);
  } else if (event.target.closest('.nav-item')) {
    // Leaving the market-data page.
    stopPhasesPolling();
  }
}

document.addEventListener('click', handleNavigation);

document.addEventListener('DOMContentLoaded', () => {
  const section = document.getElementById('market-data');
  if (section && section.classList.contains('active')) {
    refreshMarketData();
    refreshExecutionPhases();
    startPhasesPolling();
  }
});

document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    stopPhasesPolling();
  } else if (isMarketDataActive()) {
    startPhasesPolling();
    refreshExecutionPhases();
  }
});

if (typeof window !== 'undefined') {
  window.refreshMarketData = refreshMarketData;
  window.viewSymbolDetails = viewSymbolDetails;
  window.refreshExecutionPhases = refreshExecutionPhases;
}
