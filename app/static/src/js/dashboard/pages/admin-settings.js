import { fetchJson } from '../utils/network.js';

const IDS = {
  input: 'payment-address-input',
  status: 'payment-address-status',
};

function setStatus(message, tone = 'muted') {
  const el = document.getElementById(IDS.status);
  if (!el) return;
  el.textContent = message || '';
  el.classList.remove('text-success', 'text-danger', 'text-muted');
  if (tone === 'success') el.classList.add('text-success');
  else if (tone === 'error') el.classList.add('text-danger');
  else el.classList.add('text-muted');
}

async function loadPaymentSettings() {
  try {
    const data = await fetchJson('/api/admin/payment-settings');
    const input = document.getElementById(IDS.input);
    if (input) {
      input.value = data?.payment_address || '';
    }
    setStatus('');
  } catch (error) {
    console.error('Failed to load payment settings', error);
    setStatus('Unable to load payment address', 'error');
  }
}

async function savePaymentAddress() {
  const input = document.getElementById(IDS.input);
  const paymentAddress = input?.value.trim() || '';

  try {
    setStatus('Saving...', 'muted');
    const response = await fetch('/api/admin/payment-settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ payment_address: paymentAddress }),
    });
    let data = null;
    try {
      data = await response.json();
    } catch {
      data = null;
    }
    if (!response.ok || data?.error) {
      throw new Error(data?.error || 'Save failed');
    }
    input.value = data.payment_address || '';
    setStatus('Payment address saved', 'success');
  } catch (error) {
    console.error('Failed to save payment address', error);
    setStatus('Failed to save payment address', 'error');
  }
}

if (typeof window !== 'undefined') {
  window.addEventListener('dashboard:admin-settings-visible', () => loadPaymentSettings());
  document.addEventListener('DOMContentLoaded', () => {
    const section = document.getElementById('admin-settings');
    if (section && section.classList.contains('active')) {
      loadPaymentSettings();
    }
  });

  Object.assign(window, {
    savePaymentAddress,
    loadPaymentSettings,
  });
}
