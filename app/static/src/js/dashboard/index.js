import { initNavigation } from './core/navigation.js';
import { initAutoRefresh } from './core/refresh.js';
import './pages/dashboard.js';

function bootstrap() {
  initNavigation();
  initAutoRefresh();
}

document.addEventListener('DOMContentLoaded', bootstrap);
