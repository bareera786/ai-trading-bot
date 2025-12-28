import { fetchJson } from '../utils/network.js';

const IDS = {
  input: 'payment-address-input',
  status: 'payment-address-status',
};

function setStatus(message, tone = 'muted') {
  const el = document.getElementById(IDS.status);
  if (!el) return;
  el.textContent = message || '';
  const colors = {
    success: '#2ecc71',
    error: '#e74c3c',
    muted: 'var(--text-secondary)',
  };
  el.style.color = colors[tone] || colors.muted;
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
    const data = await response.json();
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
