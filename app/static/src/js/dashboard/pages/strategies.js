import { fetchJson } from '../utils/network.js';

const SELECTORS = {
  tableBody: 'strategies-table',
  activeCount: 'active-strategies-count',
  totalCount: 'total-strategies-count',
  bestName: 'best-strategy-name',
  bestPnl: 'best-strategy-pnl',
  avgWinRate: 'avg-win-rate',
  optimizationProgress: 'optimization-progress',
  optimizationStatus: 'optimization-status',
  optimizationResult: 'optimization-result',
  qfmImprovements: 'qfm-improvements',
  lastOptimization: 'last-optimization',
  autoOptimizeStatus: 'auto-optimize-status',
};

function updateText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

function statusSpan(condition, positiveLabel = 'Active', negativeLabel = 'Inactive') {
  const statusClass = condition ? 'status-success' : 'status-neutral';
  return `<span class="status-indicator ${statusClass}">${condition ? positiveLabel : negativeLabel}</span>`;
}

export async function refreshStrategies() {
  try {
    const [strategiesResponse, performanceResponse] = await Promise.all([
      fetchJson('/api/strategies'),
      fetchJson('/api/strategies/performance'),
    ]);

    const strategies = strategiesResponse?.strategies || [];
    const performance = performanceResponse?.performance || {};

    updateText(SELECTORS.activeCount, strategiesResponse?.active_count ?? strategies.filter((s) => s.active).length);
    updateText(SELECTORS.totalCount, strategiesResponse?.total_count ?? strategies.length);

    let bestStrategy = null;
    let bestPnL = -Infinity;
    let totalWinRate = 0;

    const tbody = document.getElementById(SELECTORS.tableBody);
    if (tbody) {
      tbody.innerHTML = '';
      strategies.forEach((strategy) => {
        const perf = performance[strategy.name] || {};
        const winRate = perf.win_rate || 0;
        const totalPnL = perf.total_pnl || 0;
        totalWinRate += winRate;

        if (totalPnL > bestPnL) {
          bestPnL = totalPnL;
          bestStrategy = strategy.name;
        }

        const row = document.createElement('tr');
        row.innerHTML = `
          <td>${strategy.name}</td>
          <td>${strategy.type || 'Unknown'}</td>
          <td>${statusSpan(strategy.active)}</td>
          <td>${(winRate * 100).toFixed(1)}%</td>
          <td style="color: ${totalPnL >= 0 ? 'var(--success)' : 'var(--danger)'}">$${totalPnL.toFixed(2)}</td>
          <td>${perf.total_trades || 0}</td>
          <td>${strategy.last_updated || 'Never'}</td>
          <td>
            <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 12px; margin-right: 4px;" onclick="toggleStrategy('${strategy.name}', ${!strategy.active})">
              ${strategy.active ? 'Disable' : 'Enable'}
            </button>
            <button class="btn btn-primary" style="padding: 4px 8px; font-size: 12px;" onclick="configureStrategy('${strategy.name}')">
              Configure
            </button>
          </td>
        `;
        tbody.appendChild(row);
      });
    }

    if (bestStrategy) {
      updateText(SELECTORS.bestName, bestStrategy);
      updateText(SELECTORS.bestPnl, `$${bestPnL.toFixed(2)}`);
    }

    if (strategies.length > 0) {
      const avgWinRate = (totalWinRate / strategies.length) * 100;
      updateText(SELECTORS.avgWinRate, `${avgWinRate.toFixed(1)}%`);
    }
  } catch (error) {
    console.error('Failed to refresh strategies:', error);
  }
}

export async function toggleStrategy(strategyName, enable) {
  try {
    const response = await fetch(`/api/strategies/${strategyName}/toggle`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ enable }),
    });
    const data = await response.json();
    if (data.error) {
      alert(`Error: ${data.error}`);
    } else {
      alert(data.message || 'Strategy updated');
      refreshStrategies();
    }
  } catch (error) {
    console.error('Failed to toggle strategy:', error);
    alert('Failed to toggle strategy');
  }
}

export async function configureStrategy(strategyName) {
  try {
    const strategy = await fetchJson(`/api/strategies/${strategyName}`);
    const modal = document.getElementById('strategy-config-modal');
    const content = document.getElementById('strategy-config-content');
    if (!modal || !content) return;

    content.dataset.strategyName = strategyName;
    content.innerHTML = `
      <div class="form-group">
        <label class="form-label">Strategy Type</label>
        <input type="text" class="form-input" value="${strategy.type || ''}" readonly>
      </div>
      <div class="form-group">
        <label class="form-label">Description</label>
        <textarea class="form-input" rows="3" readonly>${strategy.description || ''}</textarea>
      </div>
      <div class="form-group">
        <label class="form-label">Risk Level</label>
        <select class="form-input" id="config-risk-level">
          <option value="low" ${strategy.config?.risk_level === 'low' ? 'selected' : ''}>Low</option>
          <option value="medium" ${strategy.config?.risk_level === 'medium' ? 'selected' : ''}>Medium</option>
          <option value="high" ${strategy.config?.risk_level === 'high' ? 'selected' : ''}>High</option>
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">Max Position Size (% of portfolio)</label>
        <input type="number" class="form-input" id="config-max-position" value="${strategy.config?.max_position_size ?? 10}" min="1" max="100">
      </div>
      <div class="form-group">
        <label class="form-label">Stop Loss (%)</label>
        <input type="number" class="form-input" id="config-stop-loss" value="${strategy.config?.stop_loss ?? 2}" min="0.1" max="10" step="0.1">
      </div>
      <div class="form-group">
        <label class="form-label">Take Profit (%)</label>
        <input type="number" class="form-input" id="config-take-profit" value="${strategy.config?.take_profit ?? 5}" min="0.1" max="20" step="0.1">
      </div>
    `;

    modal.style.display = 'flex';
  } catch (error) {
    console.error('Failed to load strategy config:', error);
    alert('Failed to load strategy configuration');
  }
}

export function closeStrategyConfig() {
  const modal = document.getElementById('strategy-config-modal');
  if (modal) modal.style.display = 'none';
}

export async function saveStrategyConfig() {
  const content = document.getElementById('strategy-config-content');
  if (!content) return;
  const strategyName = content.dataset.strategyName;
  if (!strategyName) return;

  const config = {
    risk_level: document.getElementById('config-risk-level')?.value,
    max_position_size: parseFloat(document.getElementById('config-max-position')?.value ?? '0'),
    stop_loss: parseFloat(document.getElementById('config-stop-loss')?.value ?? '0'),
    take_profit: parseFloat(document.getElementById('config-take-profit')?.value ?? '0'),
  };

  try {
    const response = await fetch(`/api/strategies/${strategyName}/configure`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ config }),
    });
    const data = await response.json();
    if (data.error) {
      alert(`Error: ${data.error}`);
    } else {
      alert(data.message || 'Configuration saved');
      closeStrategyConfig();
      refreshStrategies();
    }
  } catch (error) {
    console.error('Failed to save strategy config:', error);
    alert('Failed to save strategy configuration');
  }
}

export async function resetStrategies() {
  if (!confirm('Reset all trading strategies? This will stop all active trading.')) return;
  try {
    const response = await fetch('/api/strategies/reset', {
      method: 'POST',
      credentials: 'same-origin',
    });
    const data = await response.json();
    if (data.error) {
      alert(`Error: ${data.error}`);
    } else {
      alert(data.message || 'Strategies reset');
      refreshStrategies();
    }
  } catch (error) {
    console.error('Failed to reset strategies:', error);
    alert('Failed to reset strategies');
  }
}

export async function optimizeStrategies() {
  if (!confirm('Run auto-optimization using QFM analytics? This may take several minutes.')) return;
  try {
    updateText(SELECTORS.optimizationProgress, 'Running...');
    updateText(SELECTORS.optimizationStatus, 'Optimizing strategies...');
    const data = await fetchJson('/api/strategies/optimize', { method: 'POST' });
    updateText(SELECTORS.optimizationProgress, '100%');
    updateText(SELECTORS.optimizationStatus, 'Optimization complete');
    updateText(SELECTORS.qfmImprovements, data.improvements ?? 0);
    updateText(SELECTORS.lastOptimization, new Date().toLocaleTimeString());
    updateText(SELECTORS.optimizationResult, `${data.improvements ?? 0} strategies optimized`);
    alert(`Strategy optimization complete! ${data.improvements ?? 0} strategies enhanced.`);
    refreshStrategies();
  } catch (error) {
    console.error('Strategy optimization error:', error);
    alert('Failed to optimize strategies');
    updateText(SELECTORS.optimizationProgress, '0%');
    updateText(SELECTORS.optimizationStatus, 'Optimization failed');
  }
}

export async function runQFMStrategyAnalysis() {
  try {
    updateText(SELECTORS.optimizationStatus, 'Running QFM analysis...');
    const data = await fetchJson('/api/strategies/qfm_analysis');
    if (Array.isArray(data.analysis) && data.analysis.length > 0) {
      const summary = data.analysis
        .map((item) => `${item.strategy}: ${item.recommendation}\n  QFM Score: ${item.qfm_score?.toFixed(3) ?? 'N/A'}\n  Confidence: ${((item.confidence || 0) * 100).toFixed(1)}%`)
        .join('\n\n');
      alert(`QFM Strategy Analysis Results:\n\n${summary}`);
    } else {
      alert('No QFM analysis data available.');
    }
    updateText(SELECTORS.optimizationStatus, 'QFM analysis complete');
  } catch (error) {
    console.error('QFM analysis error:', error);
    alert('Failed to run QFM analysis');
    updateText(SELECTORS.optimizationStatus, 'QFM analysis failed');
  }
}

export async function toggleAutoOptimize() {
  try {
    const data = await fetchJson('/api/strategies/auto_optimize/toggle', { method: 'POST' });
    const enabled = !!data.enabled;
    const el = document.getElementById(SELECTORS.autoOptimizeStatus);
    if (el) {
      el.textContent = enabled ? 'ENABLED' : 'DISABLED';
      el.className = `status-indicator ${enabled ? 'status-success' : 'status-neutral'}`;
    }
    alert(`Auto-optimization ${enabled ? 'enabled' : 'disabled'}`);
  } catch (error) {
    console.error('Auto-optimize toggle error:', error);
    alert('Failed to toggle auto-optimization');
  }
}

function handleSectionActivation(event) {
  if (event.target.closest('[data-page="strategies"]')) {
    setTimeout(refreshStrategies, 100);
  }
}

document.addEventListener('click', handleSectionActivation);

document.addEventListener('DOMContentLoaded', () => {
  const section = document.getElementById('strategies');
  if (section && section.classList.contains('active')) {
    refreshStrategies();
  }
});

if (typeof window !== 'undefined') {
  Object.assign(window, {
    refreshStrategies,
    toggleStrategy,
    configureStrategy,
    closeStrategyConfig,
    saveStrategyConfig,
    resetStrategies,
    optimizeStrategies,
    runQFMStrategyAnalysis,
    toggleAutoOptimize,
  });
}
