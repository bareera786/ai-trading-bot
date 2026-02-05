import '../src/js/dashboard/index.js';

// Initialize Socket.IO
const socket = io();

// Chart Instance
let performanceChart = null;

// DOM Elements
const portfolioValueEl = document.getElementById('portfolio-value');
const portfolioChangeEl = document.getElementById('portfolio-change');
const activeTradesEl = document.getElementById('active-trades');
const winRateEl = document.getElementById('win-rate');

// 1. Socket.IO Event Listeners
document.addEventListener('DOMContentLoaded', () => {

    // Connect event
    socket.on('connect', () => {
        console.log('✅ Connected to WebSocket server');
        showToast('Connected to live socket', 'success');
    });

    // Disconnect event
    socket.on('disconnect', () => {
        console.log('❌ Disconnected from WebSocket server');
        showToast('Socket connection lost', 'error');
    });

    // Real-time Trade Signal
    socket.on('trade_signal', (data) => {
        console.log('📡 Trade Signal:', data);
        const { symbol, action, price, strategy } = data;

        // Show notification
        showToast(`Signal: ${action} ${symbol} @ ${price}`, 'info');

        // Refresh dashboard data instantly
        refreshDashboardData();
    });

    // Order Fill Event
    socket.on('order_fill', (data) => {
        console.log('💰 Order Filled:', data);
        const { symbol, side, price, quantity } = data;

        showToast(`Filled: ${side} ${quantity} ${symbol} @ ${price}`, 'success');
        refreshDashboardData();
    });

    // Initial Data Load
    refreshDashboardData();
    renderPerformanceChart();
});

// 2. Dashboard Data Refresh
window.refreshDashboardData = async function () {
    try {
        const response = await fetch('/api/dashboard/stats'); // Assumption: Endpoint exists or will be mocked
        if (!response.ok) {
            // Fallback mock data if API fails (for development robustness)
            updateDashboardUI({
                portfolio_value: 12450.00,
                daily_change: 2.5,
                active_trades: 3,
                win_rate: 68
            });
            return;
        }

        const data = await response.json();
        updateDashboardUI(data);

    } catch (err) {
        console.error('Failed to fetch dashboard data:', err);
    }
};

function updateDashboardUI(data) {
    if (portfolioValueEl) portfolioValueEl.textContent = `$${data.portfolio_value.toLocaleString()}`;
    if (portfolioChangeEl) {
        const sign = data.daily_change >= 0 ? '+' : '';
        const color = data.daily_change >= 0 ? 'var(--success)' : 'var(--danger)';
        portfolioChangeEl.innerHTML = `<span style="color:${color}">${sign}${data.daily_change}%</span> today`;
    }
    if (activeTradesEl) activeTradesEl.textContent = data.active_trades;
    if (winRateEl) winRateEl.textContent = `${data.win_rate}%`;
}

// 3. Chart.js Implementation
// 3. Chart.js Implementation
async function renderPerformanceChart() {
    const ctx = document.getElementById('performance-chart');
    if (!ctx) return;

    // Destroy existing if refreshing
    if (performanceChart) performanceChart.destroy();

    // Fetch Real Data (BTC Reference for now)
    let labels = [];
    let dataPoints = [];

    try {
        const response = await fetch('/api/market-data/history/BTCUSDT');
        const result = await response.json();

        if (result.success && result.candles) {
            // Take last 30 daily candles
            const candles = result.candles.slice(-30);
            labels = candles.map(c => new Date(c.time * 1000).toLocaleDateString());
            dataPoints = candles.map(c => c.close);
        }
    } catch (e) {
        console.error("Chart data fetch failed", e);
    }

    // Default to empty if fetch failed - DO NOT SHOW FAKE DATA
    if (dataPoints.length === 0) {
        labels = ['No Data'];
        dataPoints = [0];
    }

    performanceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'BTC Reference Price ($)',
                data: dataPoints,
                borderColor: '#4299e1',
                backgroundColor: 'rgba(66, 153, 225, 0.1)',
                borderWidth: 2,
                tension: 0.4,
                fill: true,
                pointRadius: 4,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(26, 32, 44, 0.9)',
                    titleColor: '#e2e8f0',
                    bodyColor: '#e2e8f0',
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderWidth: 1
                }
            },
            scales: {
                x: {
                    grid: { display: false, drawBorder: false },
                    ticks: { color: '#718096', maxTicksLimit: 7 }
                },
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)', drawBorder: false },
                    ticks: { color: '#718096' }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
}

// 4. Toast Notification System
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    let icon = 'ℹ️';
    if (type === 'success') icon = '✅';
    if (type === 'error') icon = '❌';
    if (type === 'warning') icon = '⚠️';

    toast.innerHTML = `
        <span class="toast-icon">${icon}</span>
        <span class="toast-message">${message}</span>
    `;

    container.appendChild(toast);

    // Auto remove after 3s
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(-20px)';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Sidebar Mobile Logic (Preserved from original)
document.addEventListener('DOMContentLoaded', () => {
    const mobileToggleBtn = document.getElementById('mobile-menu-toggle-btn');
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.getElementById('mobile-overlay');
    const navItems = document.querySelectorAll('.sidebar-nav .nav-item');

    function toggleSidebar() {
        if (sidebar) sidebar.classList.toggle('active');
        if (overlay) overlay.style.display = sidebar.classList.contains('active') ? 'block' : 'none';
    }

    function closeSidebar() {
        if (sidebar) sidebar.classList.remove('active');
        if (overlay) overlay.style.display = 'none';
    }

    if (mobileToggleBtn) {
        mobileToggleBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            toggleSidebar();
        });
    }

    if (overlay) overlay.addEventListener('click', closeSidebar);
});
