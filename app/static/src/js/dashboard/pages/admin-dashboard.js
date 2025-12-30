import { apiRequest } from '../utils/api.js';
import { showNotification } from '../utils/notifications.js';

// Admin dashboard state
let adminUpdateInterval = null;

function initAdminDashboard() {
    // Initialize admin dashboard overview
    loadAdminDashboardData();

    // Set up auto-refresh for admin data (every 60 seconds)
    adminUpdateInterval = setInterval(loadAdminDashboardData, 60000);

    // Initial data load
    updateAdminDashboardData();
}

function updateAdminDashboardData() {
    // This function can be expanded to update dashboard-specific data
    console.log('Admin dashboard data updated');
}

function setupQuickAdminActions() {
    // Handle clicks on Quick Admin Actions buttons
    const actionButtons = document.querySelectorAll('[data-page]');
    actionButtons.forEach(button => {
        if (!button.classList.contains('nav-item')) { // Don't override existing nav items
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
        }
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

async function loadAdminDashboardData() {
    try {
        const response = await apiRequest('/api/admin/dashboard');

        // Update overview metrics
        updateAdminOverview(response.summary);

        // Update system health
        updateSystemHealth(response.system_status);

    } catch (error) {
        console.error('Failed to load admin dashboard data:', error);
        // Show error state for metrics
        updateAdminOverview({
            total_users: 'Error',
            active_users: 'Error',
            total_portfolio_value: 'Error',
            system_risk_level: 'unknown'
        });
    }
}

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
            alert('✅ Statistics have been reset successfully. The dashboard will refresh with new data.');
            // Refresh all dashboard data
            loadAdminDashboardData();
            // Trigger dashboard refresh
            if (window.refreshDashboardCards) {
                window.refreshDashboardCards();
            }
        } else {
            alert(`❌ Failed to reset statistics: ${response.error || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Failed to reset statistics:', error);
        alert('❌ Failed to reset statistics. Please try again.');
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

function updateSystemHealth(systemStatus) {
    // This can be expanded to show more detailed system health info
    console.log('System status:', systemStatus);
}

// Export for use in navigation
export { initAdminDashboard };

// Make resetStatistics available globally
window.resetStatistics = resetStatistics;

// Auto-initialize when admin-dashboard page is shown
window.addEventListener('dashboard:admin-dashboard-visible', () => {
    initAdminDashboard();
}, { once: true });