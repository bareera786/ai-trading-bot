import { initNavigation } from './core/navigation.js';
import { initAutoRefresh } from './core/refresh.js';
import './pages/dashboard.js';
import './pages/trading.js';
import './pages/symbols.js';
import './pages/admin-settings.js';
import './pages/admin-dashboard.js';
import './pages/backtest.js';

function bootstrap() {
  initNavigation();
  initAutoRefresh();
}

document.addEventListener('DOMContentLoaded', bootstrap);
