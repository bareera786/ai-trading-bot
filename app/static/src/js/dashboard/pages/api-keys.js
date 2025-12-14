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

    table.innerHTML = '';
    Object.entries(accounts).forEach(([key, acc]) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>Binance</td>
        <td>${acc.masked_key || 'Not set'}</td>
        <td><span class="status-indicator ${acc.connected ? 'status-success' : 'status-warning'}">${acc.connected ? 'Active' : 'Inactive'}</span></td>
        <td>${formatUpdatedAt(acc.updated_at)}</td>
        <td>
          <button class="btn btn-secondary btn-sm" data-account="${key}" onclick="openEditApiKeyModal('${key}')">Edit</button>
          <button class="btn btn-danger btn-sm" data-account="${key}" onclick="removeApiKey('${key}')">Remove</button>
        </td>
      `;
      table.appendChild(tr);
    });
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
    alert(resp.message || 'Credentials saved');
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
    }

    // Auto-load if visible
    const section = document.getElementById('api-keys');
    if (section && section.classList.contains('active')) {
      loadApiKeys();
    }
  });
}

export { loadApiKeys };
