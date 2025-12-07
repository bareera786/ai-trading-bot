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
      body: JSON.stringify({ enable: true }),
    });
    alert(data.message || 'Spot trading updated');
  } catch (error) {
    console.error('Failed to toggle spot trading:', error);
    alert('Failed to toggle spot trading');
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

export async function toggleFuturesTrading() {
  try {
    const data = await fetchJson('/api/futures/toggle', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enable: true }),
    });
    alert(data.message || 'Futures trading updated');
  } catch (error) {
    console.error('Failed to toggle futures trading:', error);
    alert('Failed to toggle futures trading');
  }
}

export async function refreshSpotData() {
  try {
    await fetchJson('/api/spot/positions');
    console.log('Spot trading data refreshed');
  } catch (error) {
    console.error('Failed to refresh spot data:', error);
  }
}

export async function refreshFuturesData() {
  try {
    await fetchJson('/api/futures/positions');
    console.log('Futures trading data refreshed');
  } catch (error) {
    console.error('Failed to refresh futures data:', error);
  }
}

if (typeof window !== 'undefined') {
  Object.assign(window, {
    executeSpotTrade,
    toggleSpotTrading,
    executeFuturesTrade,
    toggleFuturesTrading,
    refreshSpotData,
    refreshFuturesData,
  });
}
