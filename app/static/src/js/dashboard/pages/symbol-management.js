import { showNotification as showToast } from '../utils/notifications.js';

export function initSymbolManagement() {
  console.log('Initializing Symbol Management...');

  // Check user role and show appropriate sections
  checkUserRole();

  // Initialize admin symbol management if admin
  if (document.getElementById('admin-symbol-management')) {
    initAdminSymbolManagement();
  }

  // Initialize custom symbol management if premium user
  if (document.getElementById('custom-symbol-management')) {
    initCustomSymbolManagement();
  }

  // Initialize backtest modal
  initBacktestModal();

  // Initialize add symbol modal
  initAddSymbolModal();
}

// Page visibility event listener
window.addEventListener('dashboard:symbol-management-visible', () => {
  initSymbolManagement();
});

function checkUserRole() {
  // Check if user is admin
  const isAdmin = document.body.classList.contains('admin-user') ||
                  window.userRole === 'admin' ||
                  document.querySelector('[data-user-role="admin"]');

  // Check if user is premium
  const isPremium = document.body.classList.contains('premium-user') ||
                    window.userSubscription === 'premium' ||
                    document.querySelector('[data-user-subscription="premium"]');

  const adminSection = document.getElementById('admin-symbol-management');
  const customSection = document.getElementById('custom-symbol-management');
  const premiumGuard = document.getElementById('premium-guard');
  const premiumContent = document.getElementById('premium-symbols-content');

  if (isAdmin && adminSection) {
    adminSection.style.display = 'block';
  }

  if (isPremium && customSection) {
    customSection.style.display = 'block';
    if (premiumContent) premiumContent.style.display = 'block';
  } else if (!isPremium && customSection) {
    customSection.style.display = 'block';
    if (premiumGuard) premiumGuard.style.display = 'block';
  }
}

function initAdminSymbolManagement() {
  console.log('Initializing admin symbol management...');

  const searchInput = document.getElementById('admin-symbol-search');
  const statusFilter = document.getElementById('admin-symbol-status-filter');
  const refreshBtn = document.getElementById('admin-symbol-refresh-btn');
  const addSymbolBtn = document.getElementById('add-system-symbol-btn');

  // Event listeners
  if (searchInput) {
    searchInput.addEventListener('input', debounce(filterSymbols, 300));
  }

  if (statusFilter) {
    statusFilter.addEventListener('change', filterSymbols);
  }

  if (refreshBtn) {
    refreshBtn.addEventListener('click', loadAdminSymbols);
  }

  if (addSymbolBtn) {
    addSymbolBtn.addEventListener('click', () => {
      document.getElementById('add-system-symbol-modal').style.display = 'flex';
    });
  }

  // Load initial data
  loadAdminSymbols();
}

function initCustomSymbolManagement() {
  console.log('Initializing custom symbol management...');

  const addBtn = document.getElementById('custom-symbol-add');
  const saveBtn = document.getElementById('custom-symbol-save');
  const input = document.getElementById('custom-symbol-input');

  if (addBtn && input) {
    addBtn.addEventListener('click', () => {
      const symbol = input.value.trim().toUpperCase();
      if (symbol) {
        addCustomSymbol(symbol);
      }
    });

    input.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        const symbol = input.value.trim().toUpperCase();
        if (symbol) {
          addCustomSymbol(symbol);
        }
      }
    });
  }

  if (saveBtn) {
    saveBtn.addEventListener('click', saveCustomSymbols);
  }

  // Load custom symbols
  loadCustomSymbols();
}

function initBacktestModal() {
  const modal = document.getElementById('symbol-backtest-modal');
  const form = document.getElementById('symbol-backtest-form');
  const runBtn = document.getElementById('run-symbol-backtest-btn');

  if (runBtn) {
    runBtn.addEventListener('click', runSymbolBacktest);
  }
}

function initAddSymbolModal() {
  const modal = document.getElementById('add-system-symbol-modal');
  const form = document.getElementById('add-system-symbol-form');
  const submitBtn = document.getElementById('submit-add-symbol-btn');

  if (submitBtn) {
    submitBtn.addEventListener('click', addSystemSymbol);
  }
}

async function loadAdminSymbols() {
  try {
    const response = await fetch('/api/admin/symbols');
    const data = await response.json();

    if (data.success) {
      renderAdminSymbolsTable(data.symbols);
    } else {
      showToast('Failed to load symbols', 'error');
    }
  } catch (error) {
    console.error('Error loading admin symbols:', error);
    showToast('Error loading symbols', 'error');
  }
}

function renderAdminSymbolsTable(symbols) {
  const tbody = document.getElementById('admin-symbols-table');
  if (!tbody) return;

  tbody.innerHTML = symbols.map(symbol => `
    <tr>
      <td>${symbol.name}</td>
      <td><span class="status-pill status-${symbol.status}">${symbol.status}</span></td>
      <td><span class="status-pill ${symbol.model_ready ? 'status-active' : 'status-neutral'}">${symbol.model_ready ? 'Ready' : 'Training'}</span></td>
      <td>${symbol.last_trained || 'Never'}</td>
      <td>
        <div class="progress-bar">
          <div class="progress-fill" style="width: ${symbol.training_progress || 0}%"></div>
          <span class="progress-text">${symbol.training_progress || 0}%</span>
        </div>
      </td>
      <td>
        <div class="action-buttons">
          <button class="btn btn-sm btn-secondary" onclick="runBacktest('${symbol.name}')">Backtest</button>
          <button class="btn btn-sm ${symbol.status === 'active' ? 'btn-warning' : 'btn-success'}" onclick="toggleSymbolStatus('${symbol.name}')">
            ${symbol.status === 'active' ? 'Disable' : 'Enable'}
          </button>
          <button class="btn btn-sm btn-primary" onclick="retrainSymbol('${symbol.name}')">Retrain</button>
        </div>
      </td>
    </tr>
  `).join('');
}

async function loadCustomSymbols() {
  try {
    const response = await fetch('/api/user/custom-symbols');
    const data = await response.json();

    if (data.success) {
      renderCustomSymbols(data.symbols);
    }
  } catch (error) {
    console.error('Error loading custom symbols:', error);
  }
}

function renderCustomSymbols(symbols) {
  const container = document.getElementById('custom-symbols-list');
  if (!container) return;

  container.innerHTML = symbols.map(symbol => `
    <div class="pill" data-symbol="${symbol}">
      <span>${symbol}</span>
      <button onclick="removeCustomSymbol('${symbol}')" class="pill-remove">&times;</button>
    </div>
  `).join('');
}

async function addCustomSymbol(symbol) {
  // Validate symbol format
  if (!symbol.endsWith('USDT')) {
    showToast('Symbol must end with USDT', 'error');
    return;
  }

  try {
    const response = await fetch('/api/user/custom-symbols', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbol })
    });

    const data = await response.json();

    if (data.success) {
      showToast('Symbol added successfully', 'success');
      document.getElementById('custom-symbol-input').value = '';
      loadCustomSymbols();
    } else {
      showToast(data.message || 'Failed to add symbol', 'error');
    }
  } catch (error) {
    console.error('Error adding custom symbol:', error);
    showToast('Error adding symbol', 'error');
  }
}

async function saveCustomSymbols() {
  try {
    const response = await fetch('/api/user/custom-symbols/save', {
      method: 'POST'
    });

    const data = await response.json();

    if (data.success) {
      showToast('Custom symbols saved successfully', 'success');
    } else {
      showToast('Failed to save symbols', 'error');
    }
  } catch (error) {
    console.error('Error saving custom symbols:', error);
    showToast('Error saving symbols', 'error');
  }
}

async function runSymbolBacktest() {
  const symbol = document.getElementById('backtest-modal-symbol').textContent;
  const dateRange = document.getElementById('symbol-backtest-date-range').value;
  const strategy = document.getElementById('symbol-backtest-strategy').value;

  try {
    const response = await fetch('/api/symbols/backtest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbol, dateRange, strategy })
    });

    const data = await response.json();

    if (data.success) {
      document.getElementById('symbol-backtest-results').innerHTML = `
        <div class="backtest-results">
          <h4>Backtest Results</h4>
          <p>Total Return: ${data.results.total_return}%</p>
          <p>Win Rate: ${data.results.win_rate}%</p>
          <p>Max Drawdown: ${data.results.max_drawdown}%</p>
        </div>
      `;
    } else {
      showToast('Backtest failed', 'error');
    }
  } catch (error) {
    console.error('Error running backtest:', error);
    showToast('Error running backtest', 'error');
  }
}

async function addSystemSymbol() {
  const symbol = document.getElementById('new-symbol-name').value.trim().toUpperCase();
  const status = document.getElementById('new-symbol-status').value;
  const autoTrain = document.getElementById('auto-train-new-symbol').checked;

  if (!symbol) {
    showToast('Symbol name is required', 'error');
    return;
  }

  try {
    const response = await fetch('/api/admin/symbols', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbol, status, autoTrain })
    });

    const data = await response.json();

    if (data.success) {
      showToast('Symbol added successfully', 'success');
      document.getElementById('add-system-symbol-modal').style.display = 'none';
      document.getElementById('add-system-symbol-form').reset();
      loadAdminSymbols();
    } else {
      showToast(data.message || 'Failed to add symbol', 'error');
    }
  } catch (error) {
    console.error('Error adding system symbol:', error);
    showToast('Error adding symbol', 'error');
  }
}

function filterSymbols() {
  const searchTerm = document.getElementById('admin-symbol-search').value.toLowerCase();
  const statusFilter = document.getElementById('admin-symbol-status-filter').value;
  const rows = document.querySelectorAll('#admin-symbols-table tr');

  rows.forEach(row => {
    const symbol = row.cells[0].textContent.toLowerCase();
    const status = row.cells[1].textContent.toLowerCase();

    const matchesSearch = symbol.includes(searchTerm);
    const matchesStatus = !statusFilter || status === statusFilter;

    row.style.display = matchesSearch && matchesStatus ? '' : 'none';
  });
}

// Global functions for button clicks
window.runBacktest = function(symbol) {
  document.getElementById('backtest-modal-symbol').textContent = symbol;
  document.getElementById('symbol-backtest-modal').style.display = 'flex';
};

window.toggleSymbolStatus = async function(symbol) {
  try {
    const response = await fetch(`/api/admin/symbols/${symbol}/toggle`, {
      method: 'POST'
    });

    const data = await response.json();

    if (data.success) {
      showToast('Symbol status updated', 'success');
      loadAdminSymbols();
    } else {
      showToast('Failed to update symbol status', 'error');
    }
  } catch (error) {
    console.error('Error toggling symbol status:', error);
    showToast('Error updating symbol status', 'error');
  }
};

window.retrainSymbol = async function(symbol) {
  try {
    const response = await fetch(`/api/admin/symbols/${symbol}/retrain`, {
      method: 'POST'
    });

    const data = await response.json();

    if (data.success) {
      showToast('Retraining started', 'success');
      loadAdminSymbols();
    } else {
      showToast('Failed to start retraining', 'error');
    }
  } catch (error) {
    console.error('Error retraining symbol:', error);
    showToast('Error starting retraining', 'error');
  }
};

window.removeCustomSymbol = async function(symbol) {
  try {
    const response = await fetch(`/api/user/custom-symbols/${symbol}`, {
      method: 'DELETE'
    });

    const data = await response.json();

    if (data.success) {
      showToast('Symbol removed', 'success');
      loadCustomSymbols();
    } else {
      showToast('Failed to remove symbol', 'error');
    }
  } catch (error) {
    console.error('Error removing custom symbol:', error);
    showToast('Error removing symbol', 'error');
  }
};

// Utility function
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}