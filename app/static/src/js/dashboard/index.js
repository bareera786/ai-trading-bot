import { initNavigation } from './core/navigation.js';
import { initAutoRefresh } from './core/refresh.js';
import { initEventHandlers } from './core/event-handlers.js';
import { initTradeHistory } from './pages/trade-history.js';
import './pages/dashboard.js';
import './pages/trading.js';
import './pages/symbols.js';
import './pages/admin-settings.js';
import './pages/api-keys.js';
import './pages/admin-dashboard.js';
import './pages/backtest.js';
import './pages/crt-signals.js';
import './pages/health.js';

// Injected at build time by `scripts/build-assets.mjs` (esbuild define).
// eslint-disable-next-line no-undef
console.info('📦 Dashboard build loaded:', typeof BUILD_ID !== 'undefined' ? BUILD_ID : 'unknown');

import { initSubscriptionManagement } from '../admin/subscriptions.js';
import { initUserManagement } from '../admin/users.js';
import { initPlanManagement } from '../admin/plan-management.js';

function bootstrap() {
  initNavigation();
  initAutoRefresh();
  initEventHandlers();
  initTradeHistory();
  initPlanManagement(); // New Admin SaaS Plans

  // Initialize Admin Features if present
  if (document.getElementById('subscription-plans-table')) {
    initSubscriptionManagement();
  }
  if (document.getElementById('user-table-body')) {
    initUserManagement();
  }

  // Hide the loading skeleton
  const loader = document.getElementById('app-loader');
  if (loader) {
    loader.style.opacity = '0';
    setTimeout(() => {
      loader.style.display = 'none';
    }, 500);
  }
}

document.addEventListener('DOMContentLoaded', bootstrap);
