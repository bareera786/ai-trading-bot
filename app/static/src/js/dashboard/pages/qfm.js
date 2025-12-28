import { fetchJson } from '../utils/network.js';

const AGGREGATE_FIELDS = [
  'qfm_velocity',
  'qfm_acceleration',
  'qfm_jerk',
  'qfm_volume_pressure',
  'qfm_trend_confidence',
  'qfm_regime_score',
  'qfm_entropy',
];

function updateAggregate(aggregate = {}) {
  AGGREGATE_FIELDS.forEach((field) => {
    const domId = field.replace('qfm_', 'qfm-').replace(/_/g, '-');
    const el = document.getElementById(domId);
    if (el && typeof aggregate[field] === 'number') {
      el.textContent = aggregate[field].toFixed(4);
    }
  });
}

function updateSymbolTable(bySymbol = {}) {
  const tbody = document.getElementById('qfm-table-body');
  if (!tbody) return;
  tbody.innerHTML = '';
  Object.entries(bySymbol).forEach(([symbol, metrics]) => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${symbol}</td>
      <td>${(metrics.qfm_velocity ?? 0).toFixed(4)}</td>
      <td>${(metrics.qfm_acceleration ?? 0).toFixed(4)}</td>
      <td>${(metrics.qfm_jerk ?? 0).toFixed(4)}</td>
      <td>${(metrics.qfm_volume_pressure ?? 0).toFixed(4)}</td>
      <td>${(metrics.qfm_trend_confidence ?? 0).toFixed(4)}</td>
      <td>${(metrics.qfm_regime_score ?? 0).toFixed(4)}</td>
      <td>${(metrics.qfm_entropy ?? 0).toFixed(4)}</td>
    `;
    tbody.appendChild(row);
  });
}

export async function refreshQFMData() {
  try {
    const data = await fetchJson('/api/qfm');
    if (!data) return;
    updateAggregate(data.aggregate || {});
    updateSymbolTable(data.by_symbol || {});
  } catch (error) {
    console.error('Failed to refresh QFM data:', error);
  }
}

function handleSectionActivation(event) {
  if (event.target.closest('[data-page="qfm-analytics"]')) {
    setTimeout(refreshQFMData, 100);
  }
}

document.addEventListener('click', handleSectionActivation);

document.addEventListener('DOMContentLoaded', () => {
  const section = document.getElementById('qfm-analytics');
  if (section && section.classList.contains('active')) {
    refreshQFMData();
  }
});

if (typeof window !== 'undefined') {
  window.refreshQFMData = refreshQFMData;
}
