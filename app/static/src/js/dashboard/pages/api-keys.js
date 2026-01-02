import { fetchJson } from '../utils/network.js';

const IDS = {
  table: 'api-keys-table',
  addBtn: 'add-api-key-btn',
  modal: 'api-keys-modal',
  saveBtn: 'api-keys-save-btn',
  accountTypeInput: 'api-keys-account-type',
  apiKeyInput: 'api-keys-api-key',
  apiSecretInput: 'api-keys-api-secret',
  testnetInput: 'api-keys-testnet',
  noteInput: 'api-keys-note',
};

function formatUpdatedAt(ts) {
  if (!ts) return 'Never';
  try {
    const d = new Date(ts);
    return d.toLocaleString();
  } catch (e) {
    return ts;
  }
}

async function loadApiKeys() {
  const table = document.getElementById(IDS.table);
  if (!table) return;

  try {
    const status = await fetchJson('/api/binance/credentials');
    const accounts = status.accounts || {};

    // Merge spot + futures into a single row per exchange (Binance)
    const merged = {
      exchange: 'Binance',
      masked_key: null,
      connected: false,
      updated_at: null,
      types: new Set(),
      raw: {}
    };

    Object.entries(accounts).forEach(([key, acc]) => {
      // 'key' might be 'spot', 'futures', 'usdt_futures', etc.
      if (acc && acc.api_key) merged.masked_key = merged.masked_key || acc.masked_key || acc.api_key.slice(0,6) + '...';
      if (acc && acc.connected) merged.connected = merged.connected || acc.connected;
      if (acc && acc.updated_at) merged.updated_at = (!merged.updated_at || new Date(acc.updated_at) > new Date(merged.updated_at)) ? acc.updated_at : merged.updated_at;
      merged.types.add(key);
      merged.raw[key] = acc;
    });

    table.innerHTML = '';
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${merged.exchange}</td>
      <td>${merged.masked_key || 'Not set'}</td>
      <td><span class="status-indicator ${merged.connected ? 'status-success' : 'status-warning'}">${merged.connected ? 'Active' : 'Inactive'}</span></td>
      <td>${Array.from(merged.types).join(', ')}</td>
      <td>${formatUpdatedAt(merged.updated_at)}</td>
      <td>
        <button class="btn btn-secondary btn-sm" onclick="openEditApiKeyModal('spot')">Edit</button>
        <button class="btn btn-danger btn-sm" onclick="removeApiKey('spot')">Remove</button>
      </td>
    `;
    table.appendChild(tr);
  } catch (error) {
    console.error('Failed to load API keys', error);
    table.innerHTML = '<tr><td colspan="5" class="text-center text-muted">Unable to load API keys (are you logged in?)</td></tr>';
  }
}

function openAddApiKeyModal() {
  openApiKeyModal();
}

function openApiKeyModal(accountType = 'spot', existing = {}) {
  const modal = document.getElementById(IDS.modal);
  if (!modal) return;
  document.getElementById(IDS.accountTypeInput).value = accountType;
  document.getElementById(IDS.apiKeyInput).value = existing.api_key || '';
  document.getElementById(IDS.apiSecretInput).value = existing.api_secret || '';
  document.getElementById(IDS.testnetInput).checked = existing.testnet !== undefined ? !!existing.testnet : true;
  document.getElementById(IDS.noteInput).value = existing.note || '';
  modal.style.display = 'flex';
}

function closeApiKeyModal() {
  const modal = document.getElementById(IDS.modal);
  if (!modal) return;
  modal.style.display = 'none';
}

async function saveApiKey() {
  const accountType = document.getElementById(IDS.accountTypeInput).value;
  const apiKey = document.getElementById(IDS.apiKeyInput).value.trim();
  const apiSecret = document.getElementById(IDS.apiSecretInput).value.trim();
  const testnet = document.getElementById(IDS.testnetInput).checked;
  const note = document.getElementById(IDS.noteInput).value.trim();

  if (!apiKey || !apiSecret) {
    alert('API key and secret are required');
    return;
  }

  try {
    const resp = await fetchJson('/api/binance/credentials', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ apiKey, apiSecret, testnet, accountType, note }),
    });
    let msg = resp.message || 'Credentials saved';
    if (testnet) {
      msg += ' (testnet keys saved — enable real trading in System Ops to activate testnet mode)';
    }
    alert(msg);
    closeApiKeyModal();
    await loadApiKeys();
  } catch (err) {
    console.error('Failed to save API key', err);
    alert('Failed to save API key: ' + (err.message || err));
  }
}

async function removeApiKey(accountType) {
  if (!confirm(`Remove ${accountType} credentials?`)) return;
  try {
    const resp = await fetchJson('/api/binance/credentials', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ accountType }),
    });
    alert(resp.message || 'Credentials removed');
    await loadApiKeys();
  } catch (err) {
    console.error('Failed to remove API key', err);
    alert('Failed to remove API key: ' + (err.message || err));
  }
}

// Expose helper functions for inline onclicks
if (typeof window !== 'undefined') {
  window.openAddApiKeyModal = openAddApiKeyModal;
  window.openEditApiKeyModal = function (accountType) {
    // We fetch current status to prefill
    fetchJson('/api/binance/credentials')
      .then(status => {
        const acc = (status.accounts || {})[accountType] || {};
        openApiKeyModal(accountType, acc);
      })
      .catch(() => openApiKeyModal(accountType, {}));
  };
  window.removeApiKey = removeApiKey;

  document.addEventListener('dashboard:api-keys-visible', loadApiKeys);
  document.addEventListener('DOMContentLoaded', () => {
    const addBtn = document.getElementById(IDS.addBtn);
    if (addBtn) addBtn.addEventListener('click', openAddApiKeyModal);

    const modal = document.getElementById(IDS.modal);
    if (modal) {
      modal.querySelector('.modal-close')?.addEventListener('click', closeApiKeyModal);
      document.getElementById(IDS.saveBtn)?.addEventListener('click', saveApiKey);
        document.getElementById('api-keys-test-btn')?.addEventListener('click', testApiKey);
    }

    // Auto-load if visible
    const section = document.getElementById('api-keys');
    if (section && section.classList.contains('active')) {
      loadApiKeys();
    }
  });
}

export { loadApiKeys };

async function testApiKey() {
  const apiKey = document.getElementById(IDS.apiKeyInput).value.trim();
  const apiSecret = document.getElementById(IDS.apiSecretInput).value.trim();
  const testnet = document.getElementById(IDS.testnetInput).checked;

  if (!apiKey || !apiSecret) {
    alert('API key and secret are required to test');
    return;
  }

  try {
    const resp = await fetchJson('/api/binance/credentials/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ apiKey, apiSecret, testnet }),
    });
    if (resp.connected) {
      alert('Credentials validated successfully (connected)');
    } else if (resp.error) {
      alert('Validation failed: ' + resp.error);
    } else {
      alert('Validation result: ' + JSON.stringify(resp));
    }
  } catch (err) {
    console.error('Failed to test API key', err);
    alert('Failed to test API key: ' + (err.message || err));
  }
}
