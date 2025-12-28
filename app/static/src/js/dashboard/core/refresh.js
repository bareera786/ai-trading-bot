import { refreshDashboardCards, refreshRecentActivity } from '../pages/dashboard.js';
import { refreshMarketData } from '../pages/market-data.js';
import { refreshStrategies } from '../pages/strategies.js';
import { refreshQFMData } from '../pages/qfm.js';
import { refreshUsers } from '../pages/user-management.js';
import { refreshSpotData, refreshFuturesData } from '../pages/trading.js';
import { refreshCRTSignals } from '../pages/crt-signals.js';

let refreshActiveSectionRef = async () => {};

export function initAutoRefresh() {
  let refreshInterval;
  let refreshing = false;

  const start = () => {
    stop();
    refreshInterval = setInterval(refreshActiveSection, 30000);
    refreshActiveSection();
  };

  const stop = () => {
    if (refreshInterval) {
      clearInterval(refreshInterval);
      refreshInterval = null;
    }
  };

  async function refreshActiveSection() {
    if (refreshing) return;
    refreshing = true;

    try {
      const activeSection = document.querySelector('.page-section.active');
      if (!activeSection) return;

      switch (activeSection.id) {
        case 'dashboard':
          await refreshDashboardCards();
          await refreshRecentActivity();
          break;
        case 'market-data':
          await refreshMarketData();
          break;
        case 'strategies':
          await refreshStrategies();
          break;
        case 'qfm-analytics':
          await refreshQFMData();
          break;
        case 'user-management':
          await refreshUsers();
          break;
        case 'spot':
          await refreshSpotData();
          break;
        case 'futures':
          await refreshFuturesData();
          break;
        case 'crt-signals':
          await refreshCRTSignals();
          break;
        default:
          break;
      }
      updateLastRefresh();
    } catch (error) {
      console.error('Dashboard refresh error:', error);
    } finally {
      refreshing = false;
    }
  }

  function updateLastRefresh() {
    const now = new Date();
    const timeString = now.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
    document.querySelectorAll('.last-refresh-time').forEach((el) => {
      el.textContent = `Last updated: ${timeString}`;
    });
  }

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      stop();
    } else {
      start();
    }
  });

  refreshActiveSectionRef = () => refreshActiveSection();

  start();
}

if (typeof window !== 'undefined') {
  window.refreshDashboardData = () => refreshActiveSectionRef();
}
