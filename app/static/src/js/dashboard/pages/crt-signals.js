import { fetchJson } from '../utils/network.js';

export async function refreshCRTSignals() {
  try {
    const response = await fetchJson('/api/crt_data');
    if (response && response.data) {
      updateCRTSignalsTable(response.data);
    }
    console.log('CRT signals refreshed');
  } catch (error) {
    console.error('Failed to refresh CRT signals:', error);
  }
}

function updateCRTSignalsTable(signalsData) {
  const tableBody = document.getElementById('crt-signals-table');
  if (!tableBody) return;

  tableBody.innerHTML = '';

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
    emptyRow.innerHTML = '<td colspan="5" style="text-align: center; padding: var(--spacing-lg);">No CRT signals available</td>';
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
    const timestamp = new Date(signal.timestamp);
    const timeString = timestamp.toLocaleString('en-US', {
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });

    // Calculate strength (using confidence as strength indicator)
    const strength = getStrengthLabel(signal.confidence || 0);

    row.innerHTML = `
      <td>${signal.symbol}</td>
      <td><span class="status-indicator ${signalClass}">${signalText.replace('_', ' ')}</span></td>
      <td>${confidencePercent}%</td>
      <td>${timeString}</td>
      <td>${strength}</td>
    `;

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