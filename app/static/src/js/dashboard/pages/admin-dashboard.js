import { apiRequest } from '../utils/api.js';
import { showNotification } from '../utils/notifications.js';

// Self-improvement dashboard state
let siCharts = {};
let siUpdateInterval = null;

function initAdminDashboard() {
    // Initialize self-improvement dashboard
    initSelfImprovementDashboard();

    // Set up auto-refresh for self-improvement data
    siUpdateInterval = setInterval(updateSelfImprovementData, 30000); // Update every 30 seconds

    // Initial data load
    updateSelfImprovementData();
}

function initSelfImprovementDashboard() {
    // Initialize Chart.js if available
    if (typeof Chart !== 'undefined') {
        initCharts();
    }

    // Set up auto-fix button handlers
    setupAutoFixHandlers();
}

function initCharts() {
    const successCtx = document.getElementById('si-success-chart');
    const accuracyCtx = document.getElementById('si-accuracy-chart');

    if (successCtx) {
        siCharts.successRate = new Chart(successCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Success Rate %',
                    data: [],
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }

    if (accuracyCtx) {
        siCharts.accuracy = new Chart(accuracyCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Ultimate Model',
                    data: [],
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.4
                }, {
                    label: 'Optimized Model',
                    data: [],
                    borderColor: '#f59e0b',
                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100
                    }
                }
            }
        });
    }
}

function setupAutoFixHandlers() {
    // Manual cycle trigger
    const triggerCycleBtn = document.getElementById('si-trigger-cycle');
    if (triggerCycleBtn) {
        triggerCycleBtn.addEventListener('click', async () => {
            try {
                triggerCycleBtn.disabled = true;
                triggerCycleBtn.textContent = '🔄 Running...';

                const response = await apiRequest('/admin/api/self-improvement/trigger-cycle', {
                    method: 'POST'
                });

                showNotification('Self-improvement cycle triggered successfully!', 'success');
                updateSelfImprovementData(); // Refresh data immediately
            } catch (error) {
                showNotification('Failed to trigger cycle: ' + error.message, 'error');
            } finally {
                triggerCycleBtn.disabled = false;
                triggerCycleBtn.textContent = '🔄 Run Cycle Now';
            }
        });
    }

    // Model retraining
    const retrainBtn = document.getElementById('si-model-retrain');
    if (retrainBtn) {
        retrainBtn.addEventListener('click', () => triggerAutoFix('model_retraining'));
    }

    // Indicator optimization
    const optimizeBtn = document.getElementById('si-optimize-indicators');
    if (optimizeBtn) {
        optimizeBtn.addEventListener('click', () => triggerAutoFix('indicator_optimization'));
    }

    // Config reset
    const resetBtn = document.getElementById('si-reset-config');
    if (resetBtn) {
        resetBtn.addEventListener('click', () => triggerAutoFix('config_reset'));
    }

    // Memory cleanup
    const cleanupBtn = document.getElementById('si-cleanup-memory');
    if (cleanupBtn) {
        cleanupBtn.addEventListener('click', () => triggerAutoFix('memory_cleanup'));
    }
}

async function triggerAutoFix(actionType) {
    try {
        const response = await apiRequest('/admin/api/self-improvement/auto-fix', {
            method: 'POST',
            body: JSON.stringify({ action: actionType })
        });

        showNotification(`${actionType.replace('_', ' ')} completed successfully!`, 'success');
        updateSelfImprovementData();
    } catch (error) {
        showNotification(`Auto-fix failed: ${error.message}`, 'error');
    }
}

async function updateSelfImprovementData() {
    try {
        const response = await apiRequest('/admin/api/self-improvement/status');

        if (response.self_improvement) {
            updateDashboardMetrics(response.self_improvement);
            updateCharts(response.self_improvement);
            updatePerformanceTable(response.self_improvement);
        }
    } catch (error) {
        console.error('Failed to update self-improvement data:', error);
    }
}

function updateDashboardMetrics(siData) {
    // Update basic metrics
    const successRateEl = document.getElementById('si-success-rate');
    if (successRateEl && siData.last_success_rate !== undefined) {
        successRateEl.textContent = `${siData.last_success_rate.toFixed(1)}%`;
    }

    const cycleCountEl = document.getElementById('si-cycle-count');
    if (cycleCountEl && siData.cycle_count !== undefined) {
        cycleCountEl.textContent = siData.cycle_count;
    }

    const velocityEl = document.getElementById('si-velocity');
    if (velocityEl && siData.improvement_velocity !== undefined) {
        velocityEl.textContent = siData.improvement_velocity.toFixed(2);
    }

    // Update health status
    const healthEl = document.getElementById('si-health');
    const healthDescEl = document.getElementById('si-health-desc');
    if (healthEl && healthDescEl) {
        const isAutoFix = siData.auto_fix_required;
        const driftLevel = siData.drift_level || 'stable';

        healthEl.textContent = isAutoFix ? 'NEEDS ATTENTION' : 'HEALTHY';
        healthEl.className = `status-indicator ${isAutoFix ? 'status-warning' : 'status-success'}`;
        healthDescEl.textContent = isAutoFix ? `Drift detected (${driftLevel})` : 'All systems optimal';
    }

    // Update predictive analytics
    const nextPredEl = document.getElementById('si-next-prediction');
    if (nextPredEl && siData.performance_predictions && siData.performance_predictions.length > 0) {
        const nextPred = siData.performance_predictions[0];
        nextPredEl.textContent = `${nextPred.predicted_rate.toFixed(1)}% (${(nextPred.confidence * 100).toFixed(0)}% confidence)`;
    }

    const optimalTimingEl = document.getElementById('si-optimal-timing');
    if (optimalTimingEl && siData.optimal_cycle_timing) {
        const optimalTime = new Date(siData.optimal_cycle_timing);
        optimalTimingEl.textContent = optimalTime.toLocaleString();
    }

    const confidenceEl = document.getElementById('si-confidence');
    if (confidenceEl && siData.performance_predictions && siData.performance_predictions.length > 0) {
        const confidence = siData.performance_predictions[0].confidence;
        confidenceEl.textContent = `${(confidence * 100).toFixed(0)}%`;
    }

    const marketRegimeEl = document.getElementById('si-market-regime');
    if (marketRegimeEl && siData.market_regime_adaptations && siData.market_regime_adaptations.length > 0) {
        const latestRegime = siData.market_regime_adaptations[siData.market_regime_adaptations.length - 1];
        marketRegimeEl.textContent = latestRegime.regime;
    }

    // Update last auto-fix timestamp
    const lastAutoFixEl = document.getElementById('si-last-autofix');
    if (lastAutoFixEl && siData.last_auto_fix) {
        const lastFixTime = new Date(siData.last_auto_fix);
        lastAutoFixEl.textContent = lastFixTime.toLocaleString();
    }
}

function updateCharts(siData) {
    if (!siCharts.successRate || !siCharts.accuracy) return;

    // Update success rate chart
    if (siData.success_rates && siData.success_rates.length > 0) {
        const labels = siData.success_rates.map((_, i) => `Cycle ${i + 1}`);
        siCharts.successRate.data.labels = labels;
        siCharts.successRate.data.datasets[0].data = siData.success_rates;
        siCharts.successRate.update();
    }

    // Update accuracy chart
    if (siData.model_accuracy_history) {
        const ultimateData = siData.model_accuracy_history.ultimate || [];
        const optimizedData = siData.model_accuracy_history.optimized || [];

        if (ultimateData.length > 0 || optimizedData.length > 0) {
            const maxLength = Math.max(ultimateData.length, optimizedData.length);
            const labels = Array.from({ length: maxLength }, (_, i) => `Cycle ${i + 1}`);

            siCharts.accuracy.data.labels = labels;
            siCharts.accuracy.data.datasets[0].data = ultimateData;
            siCharts.accuracy.data.datasets[1].data = optimizedData;
            siCharts.accuracy.update();
        }
    }
}

function updatePerformanceTable(siData) {
    const tableBody = document.getElementById('si-performance-body');
    if (!tableBody || !siData.performance_trends) return;

    const trends = siData.performance_trends.slice(-10); // Show last 10 entries

    if (trends.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:2rem;color:#6c757d;">No performance data available</td></tr>';
        return;
    }

    tableBody.innerHTML = trends.map(trend => {
        const timestamp = new Date(trend.timestamp);
        const duration = siData.last_cycle_duration ? `${siData.last_cycle_duration.toFixed(1)}s` : 'N/A';

        return `
            <tr>
                <td style="padding:0.5rem;border:1px solid #dee2e6;">${trend.cycle_number}</td>
                <td style="padding:0.5rem;border:1px solid #dee2e6;">${timestamp.toLocaleString()}</td>
                <td style="padding:0.5rem;border:1px solid #dee2e6;">${trend.ultimate_rate.toFixed(1)}%</td>
                <td style="padding:0.5rem;border:1px solid #dee2e6;">${trend.optimized_rate.toFixed(1)}%</td>
                <td style="padding:0.5rem;border:1px solid #dee2e6;">${trend.average_rate.toFixed(1)}%</td>
                <td style="padding:0.5rem;border:1px solid #dee2e6;">${duration}</td>
            </tr>
        `;
    }).join('');
}

// Export for use in navigation
export { initAdminDashboard };

// Auto-initialize when admin-dashboard page is shown
document.addEventListener('pageChange', (e) => {
    if (e.detail.page === 'admin-dashboard') {
        initAdminDashboard();
    } else {
        // Clean up when leaving the page
        if (siUpdateInterval) {
            clearInterval(siUpdateInterval);
            siUpdateInterval = null;
        }
    }
});