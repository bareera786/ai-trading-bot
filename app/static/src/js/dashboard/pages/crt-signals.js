import { fetchJson } from '../utils/network.js';

export async function refreshCRTSignals() {
  try {
    // Try optimized signals first (often more populated), fallback to ultimate.
    const [optimizedResp, ultimateResp] = await Promise.all([
      fetchJson('/api/crt_data?mode=optimized').catch(() => null),
      fetchJson('/api/crt_data?mode=ultimate').catch(() => null),
    ]);

    const data = optimizedResp?.data && Object.keys(optimizedResp.data).length
      ? optimizedResp.data
      : ultimateResp?.data || {};

    updateCRTSignalsTable(data);
    console.log('CRT signals refreshed');
  } catch (error) {
    console.error('Failed to refresh CRT signals:', error);
    updateCRTSignalsTable({});
  }
}

function updateCRTSignalsTable(signalsData) {
  const tableBody = document.getElementById('crt-signals-table');
  if (!tableBody) return;

  tableBody.textContent = '';

  // Convert signals object to array and sort by timestamp (most recent first)
  const signalsArray = Object.entries(signalsData)
    .filter(([symbol, data]) => data && data.composite_signal)
    .map(([symbol, data]) => ({
      symbol,
      ...data.composite_signal
    }))
    .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

  if (signalsArray.length === 0) {
    const emptyRow = document.createElement('tr');
    const cell = document.createElement('td');
    cell.colSpan = 5;
    cell.className = 'text-muted';
    cell.style.textAlign = 'center';
    cell.style.padding = 'var(--spacing-lg)';
    cell.textContent = 'No CRT signals available';
    emptyRow.appendChild(cell);
    tableBody.appendChild(emptyRow);
    return;
  }

  signalsArray.forEach(signal => {
    const row = document.createElement('tr');

    // Format signal with color coding
    const signalText = signal.signal || 'UNKNOWN';
    const signalClass = getSignalClass(signalText);

    // Format confidence as percentage
    const confidencePercent = Math.round((signal.confidence || 0) * 100);

    // Format timestamp
    let timeString = '—';
    try {
      const ts = signal.timestamp ? new Date(signal.timestamp) : null;
      if (ts && !Number.isNaN(ts.getTime())) {
        timeString = ts.toLocaleString('en-US', {
          month: 'short',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit'
        });
      }
    } catch (_) {
      // ignore
    }

    // Calculate strength (using confidence as strength indicator)
    const strength = getStrengthLabel(signal.confidence || 0);

    const tdSymbol = document.createElement('td');
    tdSymbol.textContent = signal.symbol || '';

    const tdSignal = document.createElement('td');
    const badge = document.createElement('span');
    badge.className = `status-indicator ${signalClass}`;
    badge.textContent = signalText.replace('_', ' ');
    tdSignal.appendChild(badge);

    const tdConfidence = document.createElement('td');
    tdConfidence.textContent = `${confidencePercent}%`;

    const tdTime = document.createElement('td');
    tdTime.textContent = timeString;

    const tdStrength = document.createElement('td');
    tdStrength.textContent = strength;

    row.appendChild(tdSymbol);
    row.appendChild(tdSignal);
    row.appendChild(tdConfidence);
    row.appendChild(tdTime);
    row.appendChild(tdStrength);

    tableBody.appendChild(row);
  });
}

function getSignalClass(signal) {
  const signalLower = signal.toLowerCase();
  if (signalLower.includes('strong_buy')) return 'status-success';
  if (signalLower.includes('buy')) return 'status-success';
  if (signalLower.includes('strong_sell')) return 'status-danger';
  if (signalLower.includes('sell')) return 'status-danger';
  if (signalLower.includes('hold')) return 'status-warning';
  return 'status-neutral';
}

function getStrengthLabel(confidence) {
  if (confidence >= 0.8) return 'VERY STRONG';
  if (confidence >= 0.6) return 'STRONG';
  if (confidence >= 0.4) return 'MODERATE';
  if (confidence >= 0.2) return 'WEAK';
  return 'VERY WEAK';
}

if (typeof window !== 'undefined') {
  window.addEventListener('dashboard:crt-signals-visible', () => {
    refreshCRTSignals();
  });

  Object.assign(window, {
    refreshCRTSignals,
  });
}