import { apiRequest } from '../utils/api.js';
import { showNotification } from '../utils/notifications.js';

// RIBS evolution state
let ribsCharts = {};
let ribsUpdateInterval = null;
let ribsLogsAutoScroll = true;

function initAdminRIBS() {
    // Initialize RIBS monitoring
    loadRIBSData();

    // Set up control handlers
    setupRIBSControls();

    // Set up auto-refresh for RIBS data
    ribsUpdateInterval = setInterval(loadRIBSData, 30000); // Update every 30 seconds

    // Initial data load
    updateRIBSHealth();
}

function setupRIBSControls() {
    // Action button
    const actionBtn = document.getElementById('ribs-action-btn');
    if (actionBtn) {
        actionBtn.addEventListener('click', toggleRIBS);
    }

    // Pause button
    const pauseBtn = document.getElementById('ribs-pause-btn');
    if (pauseBtn) {
        pauseBtn.addEventListener('click', pauseRIBS);
    }

    // Control buttons
    const refreshBtn = document.getElementById('ribs-refresh-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => loadRIBSData());
    }

    const logsBtn = document.getElementById('ribs-logs-btn');
    if (logsBtn) {
        logsBtn.addEventListener('click', scrollToRIBSLogs);
    }

    const configBtn = document.getElementById('ribs-config-btn');
    if (configBtn) {
        configBtn.addEventListener('click', showRIBSConfig);
    }

    const exportBtn = document.getElementById('ribs-export-btn');
    if (exportBtn) {
        exportBtn.addEventListener('click', exportRIBSData);
    }

    const resetBtn = document.getElementById('ribs-reset-btn');
    if (resetBtn) {
        resetBtn.addEventListener('click', resetRIBS);
    }

    // Logs controls
    const autoScrollBtn = document.getElementById('logs-autoscroll-btn');
    if (autoScrollBtn) {
        autoScrollBtn.addEventListener('click', toggleAutoScroll);
    }

    const clearLogsBtn = document.getElementById('logs-clear-btn');
    if (clearLogsBtn) {
        clearLogsBtn.addEventListener('click', clearRIBSLogs);
    }

    const exportLogsBtn = document.getElementById('logs-export-logs-btn');
    if (exportLogsBtn) {
        exportLogsBtn.addEventListener('click', exportRIBSLogs);
    }
}

async function loadRIBSData() {
    try {
        const response = await apiRequest('/api/ribs/progress');

        if (response) {
            updateRIBSStatus(response);
            updateRIBSCharts(response);
            updateRIBSLogs(response.logs || []);
        }
    } catch (error) {
        console.error('Failed to load RIBS data:', error);
        updateRIBSStatus({ status: 'ERROR' });
    }
}

function updateRIBSStatus(data) {
    // Update status
    const statusEl = document.getElementById('ribs-status');
    if (statusEl) {
        if (data.status === 'missing') {
            statusEl.textContent = 'UNAVAILABLE';
            statusEl.className = 'text-muted';
        } else {
            const healthy = data.healthy ? 'OK' : 'STALE';
            statusEl.textContent = healthy;
            statusEl.className = data.healthy ? 'status-indicator status-success' : 'status-indicator status-warning';
        }
    }

    // Update action button
    const actionBtn = document.getElementById('ribs-action-btn');
    if (actionBtn) {
        const running = !!data.running;
        actionBtn.textContent = running ? 'Pause Evolution' : 'Start Evolution';
        actionBtn.disabled = false;
    }

    // Update progress
    const progressEl = document.getElementById('ribs-progress');
    const progressBarEl = document.getElementById('ribs-progress-bar');
    if (progressEl && data.progress !== undefined) {
        progressEl.textContent = `${data.progress.toFixed(1)}%`;
        if (progressBarEl) {
            progressBarEl.style.width = `${data.progress}%`;
        }
    }

    // Update generations
    const generationsEl = document.getElementById('ribs-generations');
    if (generationsEl && data.generations !== undefined) {
        generationsEl.textContent = data.generations;
    }

    // Update fitness
    const fitnessEl = document.getElementById('ribs-fitness');
    if (fitnessEl && data.fitness !== undefined) {
        fitnessEl.textContent = data.fitness.toFixed(3);
    }

    // Update last checkpoint
    const checkpointEl = document.getElementById('ribs-last-checkpoint');
    if (checkpointEl) {
        const age = data.latest_checkpoint_age_seconds;
        checkpointEl.textContent = age != null ? `Last checkpoint: ${age}s ago` : 'Last checkpoint: unknown';
    }
}

function updateRIBSCharts(data) {
    // Update diversity chart
    if (data.diversity_history) {
        updateChart('ribs-diversity-chart', data.diversity_history);
    }

    // Update mutation rate chart
    if (data.mutation_history) {
        updateChart('ribs-mutation-chart', data.mutation_history);
    }

    // Update selection pressure chart
    if (data.selection_history) {
        updateChart('ribs-selection-chart', data.selection_history);
    }
}

function updateChart(chartId, data) {
    // Simple chart update - in production this would use Chart.js
    const chartEl = document.getElementById(chartId);
    if (chartEl && data.length > 0) {
        const latestValue = data[data.length - 1];
        const valueEl = chartEl.parentElement.querySelector('.metric-value');
        if (valueEl) {
            valueEl.textContent = latestValue.toFixed(3);
        }
    }
}

function updateRIBSLogs(logs) {
    const logsContainer = document.getElementById('ribs-logs-section');
    if (!logsContainer) return;

    if (logs.length === 0) {
        logsContainer.innerHTML = `
            <div class="log-entry log-info">
                <span class="log-timestamp">${new Date().toLocaleString()}</span>
                <span class="log-level">INFO</span>
                <span class="log-message">RIBS evolution system initialized</span>
            </div>
        `;
        return;
    }

    logsContainer.innerHTML = logs.slice(-50).map(log => {
        const timestamp = new Date(log.timestamp * 1000).toLocaleString();
        const level = log.level || 'info';
        const message = log.message || '';

        return `
            <div class="log-entry log-${level}">
                <span class="log-timestamp">${timestamp}</span>
                <span class="log-level">${level.toUpperCase()}</span>
                <span class="log-message">${message}</span>
            </div>
        `;
    }).join('');

    // Auto-scroll if enabled
    if (ribsLogsAutoScroll) {
        logsContainer.scrollTop = logsContainer.scrollHeight;
    }
}

async function toggleRIBS() {
    const actionBtn = document.getElementById('ribs-action-btn');
    if (!actionBtn) return;

    try {
        actionBtn.disabled = true;
        const isRunning = actionBtn.textContent.includes('Pause');

        const url = isRunning ? '/api/ribs/pause' : '/api/ribs/start';
        const response = await apiRequest(url, { method: 'POST' });

        showNotification(`RIBS evolution ${isRunning ? 'paused' : 'started'} successfully!`, 'success');
        setTimeout(loadRIBSData, 1000); // Refresh after 1 second
    } catch (error) {
        showNotification('Failed to toggle RIBS evolution: ' + error.message, 'error');
        actionBtn.disabled = false;
    }
}

async function pauseRIBS() {
    // Similar to toggle but specifically for pause
    await toggleRIBS();
}

function scrollToRIBSLogs() {
    const logsSection = document.getElementById('ribs-logs-section');
    if (logsSection) {
        logsSection.scrollIntoView({ behavior: 'smooth' });
    }
}

function showRIBSConfig() {
    showNotification('RIBS configuration panel coming soon!', 'info');
}

async function exportRIBSData() {
    try {
        const response = await apiRequest('/api/ribs/export');
        const blob = new Blob([JSON.stringify(response, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `ribs-data-${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        URL.revokeObjectURL(url);
        showNotification('RIBS data exported successfully!', 'success');
    } catch (error) {
        showNotification('Failed to export RIBS data: ' + error.message, 'error');
    }
}

async function resetRIBS() {
    if (!confirm('⚠️ WARNING: This will reset the entire RIBS evolution system and all progress will be lost. Are you sure?')) {
        return;
    }

    try {
        const response = await apiRequest('/api/ribs/reset', { method: 'POST' });
        showNotification('RIBS evolution reset successfully!', 'success');
        loadRIBSData(); // Refresh data
    } catch (error) {
        showNotification('Failed to reset RIBS: ' + error.message, 'error');
    }
}

function toggleAutoScroll() {
    ribsLogsAutoScroll = !ribsLogsAutoScroll;
    const btn = document.getElementById('logs-autoscroll-btn');
    if (btn) {
        btn.textContent = ribsLogsAutoScroll ? 'Disable Auto-scroll' : 'Enable Auto-scroll';
    }
}

async function clearRIBSLogs() {
    try {
        await apiRequest('/api/ribs/logs/clear', { method: 'POST' });
        const logsContainer = document.getElementById('ribs-logs-section');
        if (logsContainer) {
            logsContainer.innerHTML = '';
        }
        showNotification('RIBS logs cleared successfully!', 'success');
    } catch (error) {
        showNotification('Failed to clear logs: ' + error.message, 'error');
    }
}

async function exportRIBSLogs() {
    try {
        const response = await apiRequest('/api/ribs/logs');
        const logs = response.logs || [];
        const logText = logs.map(log => {
            const timestamp = new Date(log.timestamp * 1000).toLocaleString();
            return `[${timestamp}] ${log.level.toUpperCase()}: ${log.message}`;
        }).join('\n');

        const blob = new Blob([logText], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `ribs-logs-${new Date().toISOString().split('T')[0]}.txt`;
        a.click();
        URL.revokeObjectURL(url);
        showNotification('RIBS logs exported successfully!', 'success');
    } catch (error) {
        showNotification('Failed to export logs: ' + error.message, 'error');
    }
}

async function updateRIBSHealth() {
    // Update RIBS health status
    try {
        const response = await apiRequest('/api/ribs/progress');
        updateRIBSStatus(response);
    } catch (error) {
        console.error('Failed to update RIBS health:', error);
    }
}

// Export for use in navigation
export { initAdminRIBS };

// Auto-initialize when admin-ribs page is shown
window.addEventListener('dashboard:admin-ribs-visible', () => {
    initAdminRIBS();
}, { once: true });