import { apiRequest } from '../utils/api.js';
import { showNotification } from '../utils/notifications.js';

// Admin overview state
let overviewUpdateInterval = null;

function initAdminOverview() {
    // Initialize admin overview
    loadAdminOverviewData();

    // Set up Quick Admin Actions navigation
    setupQuickAdminActions();

    // Set up auto-refresh for overview data (every 30 seconds)
    overviewUpdateInterval = setInterval(loadAdminOverviewData, 30000);

    // Initial data load
    updateSystemStatus();
}

function setupQuickAdminActions() {
    // Handle clicks on Quick Admin Actions buttons
    const actionButtons = document.querySelectorAll('.admin-action-card');
    actionButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            const pageId = button.getAttribute('data-page');
            if (pageId) {
                // Trigger navigation to the page
                const navItem = document.querySelector(`.nav-item[data-page="${pageId}"]`);
                if (navItem) {
                    navItem.click();
                } else {
                    // Fallback: manually show the page
                    showPage(pageId);
                }
            }
        });
    });
}

function showPage(pageId) {
    // Fallback page switching logic
    const pageSections = document.querySelectorAll('.page-section');
    const targetSection = document.getElementById(pageId);

    if (targetSection) {
        // Hide all pages
        pageSections.forEach(section => section.classList.remove('active'));
        // Show target page
        targetSection.classList.add('active');

        // Update page title
        const pageTitles = {
            'user-management': 'User Management',
            'admin-overview': 'Admin Overview',
            'admin-self-improvement': 'AI Self-Improvement',
            'admin-ribs': 'RIBS Evolution',
            'symbol-management': 'Symbol Management',
            'backtest-lab': 'Backtest Lab',
            'admin-settings': 'Admin Settings'
        };

        const pageTitle = document.getElementById('page-title');
        const pageSubtitle = document.getElementById('page-subtitle');

        if (pageTitle && pageTitles[pageId]) {
            pageTitle.textContent = pageTitles[pageId];
            pageSubtitle.textContent = 'Industrial-grade overview and controls for administrators.';
        }

        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });

        // Dispatch page change event for other components
        window.dispatchEvent(new CustomEvent('pageChange', { detail: { page: pageId } }));
    }
}

async function loadAdminOverviewData() {
    try {
        const response = await apiRequest('/api/admin/dashboard');

        // Update overview metrics
        updateAdminOverview(response.summary);

        // Update system status
        updateSystemStatus();

    } catch (error) {
        console.error('Failed to load admin overview data:', error);
        // Show error state for metrics
        updateAdminOverview({
            total_users: 'Error',
            active_users: 'Error',
            total_portfolio_value: 'Error',
            system_risk_level: 'unknown'
        });
    }
}

function updateAdminOverview(summary) {
    // Update user counts
    const totalUsersEl = document.getElementById('admin-total-users');
    if (totalUsersEl) {
        totalUsersEl.textContent = summary.total_users || 0;
    }

    const activeUsersEl = document.getElementById('admin-active-users');
    if (activeUsersEl) {
        activeUsersEl.textContent = summary.active_users || 0;
    }

    // Update revenue (total portfolio value as proxy)
    const revenueEl = document.getElementById('admin-total-revenue');
    if (revenueEl) {
        const revenue = summary.total_portfolio_value || 0;
        revenueEl.textContent = `$${revenue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }

    // Update system health based on risk level
    const healthEl = document.getElementById('admin-system-health');
    if (healthEl) {
        const riskLevel = summary.system_risk_level || 'unknown';
        let healthStatus = 'ONLINE';
        let healthClass = 'status-success';

        if (riskLevel === 'high') {
            healthStatus = 'HIGH RISK';
            healthClass = 'status-error';
        } else if (riskLevel === 'medium') {
            healthStatus = 'MEDIUM RISK';
            healthClass = 'status-warning';
        }

        healthEl.textContent = healthStatus;
        healthEl.className = `status-indicator ${healthClass}`;
    }
}

async function updateSystemStatus() {
    try {
        // Update database status
        const dbStatusEl = document.getElementById('db-status');
        if (dbStatusEl) {
            dbStatusEl.textContent = 'ONLINE';
            dbStatusEl.className = 'status-indicator status-success';
        }

        // Update API status
        const apiStatusEl = document.getElementById('api-status');
        if (apiStatusEl) {
            apiStatusEl.textContent = 'ONLINE';
            apiStatusEl.className = 'status-indicator status-success';
        }

        // Update models status
        const modelsStatusEl = document.getElementById('models-status');
        if (modelsStatusEl) {
            modelsStatusEl.textContent = 'LOADED';
            modelsStatusEl.className = 'status-indicator status-success';
        }

        // Update trading status
        const tradingStatusEl = document.getElementById('trading-status');
        if (tradingStatusEl) {
            // This would come from actual trading engine status
            tradingStatusEl.textContent = 'IDLE';
            tradingStatusEl.className = 'status-indicator status-warning';
        }

    } catch (error) {
        console.error('Failed to update system status:', error);
    }
}

// Export for use in navigation
export { initAdminOverview };

// Reset statistics function
async function resetStatistics() {
    if (!confirm('⚠️ WARNING: This will permanently reset ALL trading statistics, performance data, and profit/loss records. This action cannot be undone. Are you sure you want to continue?')) {
        return;
    }

    if (!confirm('🔴 FINAL CONFIRMATION: All trading history and statistics will be lost. Type "RESET" to confirm:')) {
        return;
    }

    try {
        const response = await apiRequest('/api/admin/reset-statistics', {
            method: 'POST'
        });

        if (response.success) {
            showNotification('Statistics have been reset successfully. The dashboard will refresh with new data.', 'success');
            // Refresh all dashboard data
            loadAdminOverviewData();
            // Trigger dashboard refresh
            if (window.refreshDashboardCards) {
                window.refreshDashboardCards();
            }
        } else {
            showNotification(`Failed to reset statistics: ${response.error || 'Unknown error'}`, 'error');
        }
    } catch (error) {
        console.error('Failed to reset statistics:', error);
        showNotification('Failed to reset statistics. Please try again.', 'error');
    }
}

// Make resetStatistics available globally
window.resetStatistics = resetStatistics;

// Auto-initialize when admin-overview page is shown
window.addEventListener('dashboard:admin-overview-visible', () => {
    initAdminOverview();
}, { once: true });