/**
 * Global event handler wiring to replace inline onclick attributes
 * This eliminates CSP inline-script violations
 */

export function initEventHandlers() {
  // Navigation & modal handlers
  document.addEventListener('DOMContentLoaded', () => {
    // Mobile menu toggle
    document.getElementById('mobile-menu-toggle')?.addEventListener('click', () => {
      const sidebar = document.querySelector('.sidebar');
      const toggle = document.getElementById('mobile-menu-toggle');
      const overlay = document.querySelector('.sidebar-overlay');
      if (sidebar) sidebar.classList.toggle('open');
      if (toggle) toggle.classList.toggle('active');
      if (overlay) overlay.classList.toggle('active');
    });

    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', (e) => {
      const sidebar = document.querySelector('.sidebar');
      const toggle = document.getElementById('mobile-menu-toggle');
      const overlay = document.querySelector('.sidebar-overlay');
      const target = e.target;

      if (window.innerWidth <= 1024 &&
          sidebar &&
          toggle &&
          overlay &&
          !sidebar.contains(target) &&
          !toggle.contains(target) &&
          sidebar.classList.contains('open')) {
        sidebar.classList.remove('open');
        toggle.classList.remove('active');
        overlay.classList.remove('active');
      }
    });

    // Logout button
    document.getElementById('logout-btn')?.addEventListener('click', () => {
      window.location.href = '/logout';
    });

    // RIBS logs handlers
    document.getElementById('refresh-ribs-logs-btn')?.addEventListener('click', async () => {
      if (window.refreshRIBSLogs) {
        await window.refreshRIBSLogs();
      }
      const el = document.getElementById('ribs-logs-section');
      if (el) el.scrollIntoView({ behavior: 'smooth' });
    });

    document.getElementById('scroll-ribs-logs-btn')?.addEventListener('click', () => {
      const el = document.getElementById('ribs-logs-section');
      if (el) el.scrollIntoView({ behavior: 'smooth' });
    });

    // Backtest run button
    document.getElementById('run-backtest-btn')?.addEventListener('click', async () => {
      if (window.runBacktest) {
        await window.runBacktest();
      }
    });

    // Dashboard refresh button
    document.getElementById('refresh-dashboard-btn')?.addEventListener('click', async () => {
      if (window.refreshDashboardData) {
        await window.refreshDashboardData();
      }
    });

    // Strategy buttons
    document.getElementById('reset-strategies-btn')?.addEventListener('click', async () => {
      if (window.resetStrategies) {
        await window.resetStrategies();
      }
    });

    document.getElementById('refresh-strategies-btn')?.addEventListener('click', async () => {
      if (window.refreshStrategies) {
        await window.refreshStrategies();
      }
    });

    document.getElementById('optimize-strategies-btn')?.addEventListener('click', async () => {
      if (window.optimizeStrategies) {
        await window.optimizeStrategies();
      }
    });

    document.getElementById('qfm-analysis-btn')?.addEventListener('click', async () => {
      if (window.runQFMStrategyAnalysis) {
        await window.runQFMStrategyAnalysis();
      }
    });

    // CRT signals refresh
    document.getElementById('refresh-crt-signals-btn')?.addEventListener('click', async () => {
      if (window.refreshCRTSignals) {
        await window.refreshCRTSignals();
      }
    });

    // Modal close buttons (symbol backtest modal)
    document.querySelectorAll('[data-close-modal]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const modalId = btn.getAttribute('data-close-modal');
        const modal = document.getElementById(modalId);
        if (modal) modal.style.display = 'none';
      });
    });

    // Strategy config close buttons
    document.querySelectorAll('[data-close-strategy-config]').forEach((btn) => {
      btn.addEventListener('click', async () => {
        if (window.closeStrategyConfig) {
          await window.closeStrategyConfig();
        }
      });
    });

    // Strategy config cancel/save
    document.getElementById('strategy-config-cancel-btn')?.addEventListener('click', async () => {
      if (window.closeStrategyConfig) {
        await window.closeStrategyConfig();
      }
    });

    document.getElementById('strategy-config-save-btn')?.addEventListener('click', async () => {
      if (window.saveStrategyConfig) {
        await window.saveStrategyConfig();
      }
    });
  });
}

// Export handlers for global access if needed
export const handlers = {
  toggleSidebar: () => {
    const sidebar = document.querySelector('.sidebar');
    if (sidebar) sidebar.classList.toggle('open');
  },
  logout: () => {
    window.location.href = '/logout';
  },
};

if (typeof window !== 'undefined') {
  window.toggleSidebar = handlers.toggleSidebar;
  window.logout = handlers.logout;
}
