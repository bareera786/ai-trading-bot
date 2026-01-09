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

function bootstrap() {
  initNavigation();
  initAutoRefresh();
  initEventHandlers();
  initTradeHistory();
}

document.addEventListener('DOMContentLoaded', bootstrap);
