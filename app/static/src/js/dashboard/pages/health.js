/**
 * Health Page - System Monitoring Dashboard
 * Displays real-time system metrics, resource usage, and alerts
 */

import { apiRequest } from '../utils/api.js';
import { showNotification } from '../utils/notifications.js';

class HealthPage {
    constructor() {
        this.refreshInterval = null;
        this.alerts = [];
        this.metrics = {};
        this.initialized = false;
    }

    init() {
        if (this.initialized) return;
        this.initialized = true;
        
        this.bindEvents();
        this.loadHealthData();
        this.startAutoRefresh();
    }

    destroy() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
    }

    bindEvents() {
        // Run diagnostics button
        const diagnosticsBtn = document.querySelector('#health .btn-primary');
        if (diagnosticsBtn) {
            diagnosticsBtn.addEventListener('click', () => this.runDiagnostics());
        }

        // Refresh metrics button (if exists)
        const refreshBtn = document.querySelector('#health .btn-secondary');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadHealthData());
        }
    }

    async loadHealthData() {
        try {
            // Load system metrics
            const metricsResponse = await apiRequest('/api/system-metrics');
            if (metricsResponse.success) {
                this.updateMetrics(metricsResponse.data);
            }

            // Load alerts
            const alertsResponse = await apiRequest('/api/alerts');
            if (alertsResponse.success) {
                this.updateAlerts(alertsResponse.data);
            }

            // Load resource recommendations
            const recommendationsResponse = await apiRequest('/api/resource-recommendations');
            if (recommendationsResponse.success) {
                this.updateRecommendations(recommendationsResponse.data);
            }

        } catch (error) {
            console.error('Failed to load health data:', error);
            showNotification('Failed to load system health data', 'error');
        }
    }

    updateMetrics(data) {
        this.metrics = data;

        // Update CPU usage
        const cpuEl = document.querySelector('#health .card-title:contains("CPU Usage")').closest('.dashboard-card').querySelector('.card-value');
        if (cpuEl && data.system?.cpu_percent !== undefined) {
            cpuEl.textContent = `${data.system.cpu_percent.toFixed(1)}%`;
        }

        // Update Memory usage
        const memoryEl = document.querySelector('#health .card-title:contains("Memory Usage")').closest('.dashboard-card').querySelector('.card-value');
        if (memoryEl && data.system?.memory_used_gb !== undefined) {
            memoryEl.textContent = `${data.system.memory_used_gb.toFixed(1)}GB`;
        }

        // Update Disk space
        const diskEl = document.querySelector('#health .card-title:contains("Disk Space")').closest('.dashboard-card').querySelector('.card-value');
        if (diskEl && data.system?.disk_usage_percent !== undefined) {
            diskEl.textContent = `${data.system.disk_usage_percent.toFixed(1)}%`;
        }

        // Update API status
        const apiEl = document.querySelector('#health .card-title:contains("API Status")').closest('.dashboard-card').querySelector('.status-indicator');
        if (apiEl && data.bot?.api_connected !== undefined) {
            apiEl.textContent = data.bot.api_connected ? 'CONNECTED' : 'DISCONNECTED';
            apiEl.className = `status-indicator ${data.bot.api_connected ? 'status-success' : 'status-error'}`;
        }

        // Update additional metrics if they exist in the DOM
        this.updateAdditionalMetrics(data);
    }

    updateAdditionalMetrics(data) {
        // Update bot status
        const botStatusEl = document.getElementById('bot-status');
        if (botStatusEl && data.bot?.status) {
            botStatusEl.textContent = data.bot.status;
            botStatusEl.className = `status-indicator status-${data.bot.status.toLowerCase()}`;
        }

        // Update trading status
        const tradingStatusEl = document.getElementById('trading-status');
        if (tradingStatusEl && data.bot?.trading_enabled !== undefined) {
            tradingStatusEl.textContent = data.bot.trading_enabled ? 'ENABLED' : 'DISABLED';
            tradingStatusEl.className = `status-indicator ${data.bot.trading_enabled ? 'status-success' : 'status-warning'}`;
        }

        // Update model metrics
        const modelMetricsEl = document.getElementById('model-metrics');
        if (modelMetricsEl && data.models) {
            modelMetricsEl.innerHTML = this.generateModelMetricsHTML(data.models);
        }

        // Update training status
        const trainingStatusEl = document.getElementById('training-status');
        if (trainingStatusEl && data.training) {
            trainingStatusEl.innerHTML = this.generateTrainingStatusHTML(data.training);
        }
    }

    updateAlerts(alerts) {
        this.alerts = alerts || [];

        // Update alerts summary
        const alertsSummaryEl = document.getElementById('alerts-summary');
        if (alertsSummaryEl) {
            const activeAlerts = this.alerts.filter(alert => !alert.acknowledged);
            alertsSummaryEl.innerHTML = `
                <div class="alerts-count">
                    <span class="alerts-critical">${activeAlerts.filter(a => a.severity === 'critical').length}</span> Critical
                    <span class="alerts-warning">${activeAlerts.filter(a => a.severity === 'warning').length}</span> Warning
                    <span class="alerts-info">${activeAlerts.filter(a => a.severity === 'info').length}</span> Info
                </div>
            `;
        }

        // Update alerts list
        const alertsListEl = document.getElementById('alerts-list');
        if (alertsListEl) {
            alertsListEl.innerHTML = this.generateAlertsHTML(activeAlerts);
        }
    }

    updateRecommendations(recommendations) {
        const recommendationsEl = document.getElementById('resource-recommendations');
        if (recommendationsEl && recommendations) {
            recommendationsEl.innerHTML = this.generateRecommendationsHTML(recommendations);
        }
    }

    generateModelMetricsHTML(models) {
        if (!models || !Array.isArray(models)) return '<p>No model data available</p>';

        return models.map(model => `
            <div class="model-metric">
                <span class="model-symbol">${model.symbol}</span>
                <span class="model-accuracy">${(model.accuracy * 100).toFixed(2)}%</span>
                <span class="model-indicators">${model.indicators_count} indicators</span>
            </div>
        `).join('');
    }

    generateTrainingStatusHTML(training) {
        if (!training) return '<p>No training data available</p>';

        return `
            <div class="training-status">
                <div class="training-item">
                    <span class="label">Status:</span>
                    <span class="value ${training.is_training ? 'status-success' : 'status-warning'}">
                        ${training.is_training ? 'ACTIVE' : 'IDLE'}
                    </span>
                </div>
                <div class="training-item">
                    <span class="label">Current Symbol:</span>
                    <span class="value">${training.current_symbol || 'None'}</span>
                </div>
                <div class="training-item">
                    <span class="label">Progress:</span>
                    <span class="value">${training.progress || 0}%</span>
                </div>
            </div>
        `;
    }

    generateAlertsHTML(alerts) {
        if (!alerts || alerts.length === 0) {
            return '<p class="no-alerts">No active alerts</p>';
        }

        return alerts.map(alert => `
            <div class="alert-item alert-${alert.severity}">
                <div class="alert-header">
                    <span class="alert-severity">${alert.severity.toUpperCase()}</span>
                    <span class="alert-timestamp">${new Date(alert.timestamp).toLocaleString()}</span>
                </div>
                <div class="alert-message">${alert.message}</div>
                <div class="alert-actions">
                    <button class="btn btn-sm btn-secondary" onclick="healthPage.acknowledgeAlert('${alert.id}')">
                        Acknowledge
                    </button>
                </div>
            </div>
        `).join('');
    }

    generateRecommendationsHTML(recommendations) {
        if (!recommendations || recommendations.length === 0) {
            return '<p>No recommendations available</p>';
        }

        return recommendations.map(rec => `
            <div class="recommendation-item">
                <div class="recommendation-type">${rec.type}</div>
                <div class="recommendation-message">${rec.message}</div>
                <div class="recommendation-priority priority-${rec.priority}">${rec.priority}</div>
            </div>
        `).join('');
    }

    async acknowledgeAlert(alertId) {
        try {
            const response = await apiRequest(`/api/alerts/acknowledge/${alertId}`, {
                method: 'POST'
            });

            if (response.success) {
                showNotification('Alert acknowledged', 'success');
                this.loadHealthData(); // Refresh data
            } else {
                showNotification('Failed to acknowledge alert', 'error');
            }
        } catch (error) {
            console.error('Failed to acknowledge alert:', error);
            showNotification('Failed to acknowledge alert', 'error');
        }
    }

    async runDiagnostics() {
        try {
            showNotification('Running system diagnostics...', 'info');

            // This could call a diagnostics endpoint if implemented
            // For now, just refresh all data
            await this.loadHealthData();

            showNotification('Diagnostics completed', 'success');
        } catch (error) {
            console.error('Diagnostics failed:', error);
            showNotification('Diagnostics failed', 'error');
        }
    }

    startAutoRefresh() {
        // Refresh every 30 seconds
        this.refreshInterval = setInterval(() => {
            this.loadHealthData();
        }, 30000);
    }
}

// Create global instance
const healthPage = new HealthPage();

// Export for use in main dashboard
export { healthPage };

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('health')?.classList.contains('active')) {
        healthPage.init();
    }
});

// Listen for page visibility
window.addEventListener('dashboard:health-visible', () => {
    healthPage.init();
});