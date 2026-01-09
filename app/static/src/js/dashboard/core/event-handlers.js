/**
 * Global event handler wiring to replace inline onclick attributes
 * This eliminates CSP inline-script violations
 */

export function initEventHandlers() {
  // Navigation & modal handlers
  document.addEventListener('DOMContentLoaded', () => {
    // Mobile menu toggle
    document.getElementById('mobile-menu-toggle-btn')?.addEventListener('click', () => {
      const sidebar = document.querySelector('.sidebar');
      if (sidebar) sidebar.classList.toggle('open');
    });

    // Logout button - use fetch to capture server response and log details
    document.getElementById('logout-btn')?.addEventListener('click', async (ev) => {
      ev.preventDefault();
      console.info('[logout] Logout button clicked - initiating logout flow');
      try {
        // Call server logout endpoint and allow redirects
        const resp = await fetch('/logout', { method: 'GET', credentials: 'same-origin' });
        console.info('[logout] /logout response', { status: resp.status, redirected: resp.redirected, url: resp.url });

        if (resp.redirected) {
          // Server asked to redirect (common behavior) — follow it in the browser
          console.info('[logout] Server redirected to', resp.url);
          // clear any client-side ephemeral state, then redirect to /login
          try { sessionStorage.clear(); localStorage.clear(); } catch (e) {}
          window.location.href = '/login';
          return;
        }

        // If server returned OK (200/204/202), navigate to login page
        if (resp.ok) {
          console.info('[logout] Logout successful, navigating to /login');
          try { sessionStorage.clear(); localStorage.clear(); } catch (e) {}
          window.location.href = '/login';
          return;
        }

        // Otherwise, show error and still navigate to login to clear client state
        console.warn('[logout] Unexpected logout response, forcing navigation to /login');
        try { sessionStorage.clear(); localStorage.clear(); } catch (e) {}
        window.location.href = '/login';
      } catch (err) {
        console.error('[logout] Error during logout fetch', err);
        // Fallback: navigate to `/login` to ensure client appears logged out
        window.location.href = '/login';
      }
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

    // Admin settings: payment address
    document.getElementById('admin-settings-reset-btn')?.addEventListener('click', async () => {
      if (window.loadPaymentSettings) {
        await window.loadPaymentSettings();
      }
    });

    document.getElementById('admin-settings-save-btn')?.addEventListener('click', async () => {
      if (window.savePaymentAddress) {
        await window.savePaymentAddress();
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
    // Prefer the fetch-based logout flow to capture server responses
    if (typeof window !== 'undefined' && window.document) {
      const btn = document.getElementById('logout-btn');
      if (btn) {
        btn.click();
        return;
      }
    }
    // Last-resort: direct navigation
    window.location.href = '/logout';
  },
};

if (typeof window !== 'undefined') {
  window.toggleSidebar = handlers.toggleSidebar;
  window.logout = handlers.logout;
}
