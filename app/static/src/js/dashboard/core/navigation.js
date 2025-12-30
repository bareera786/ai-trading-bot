export function initNavigation() {
  const navItems = document.querySelectorAll('.nav-item');
  const pageSections = document.querySelectorAll('.page-section');
  const pageTitle = document.getElementById('page-title');
  const pageSubtitle = document.getElementById('page-subtitle');

  // Mobile menu toggle
  const mobileMenuToggle = document.getElementById('mobile-menu-toggle-btn');
  const sidebar = document.querySelector('.sidebar');
  const sidebarOverlay = document.createElement('div');
  sidebarOverlay.className = 'sidebar-overlay';
  document.body.appendChild(sidebarOverlay);

  if (mobileMenuToggle && sidebar) {
    mobileMenuToggle.addEventListener('click', () => {
      sidebar.classList.toggle('open');
      sidebarOverlay.classList.toggle('active');
    });

    sidebarOverlay.addEventListener('click', () => {
      sidebar.classList.remove('open');
      sidebarOverlay.classList.remove('active');
    });
  }

  const pageInfo = {
    dashboard: { title: 'Dashboard', subtitle: 'Overview of your trading bot performance' },
    'market-data': { title: 'Market Data', subtitle: 'Real-time market data and AI signals' },
    'symbol-management': { title: 'Symbol Management', subtitle: 'Manage trading symbols, custom pairs, and model training configurations' },
    spot: { title: 'Spot Trading', subtitle: 'Spot trading management and positions' },
    futures: { title: 'Futures', subtitle: 'Futures trading management' },
    strategies: { title: 'Strategies', subtitle: 'Trading strategy management and performance' },
    'crt-signals': { title: 'CRT Signals', subtitle: 'CRT signal analysis and predictions' },
    'trade-history': { title: 'Trade History', subtitle: 'Historical trading performance' },
    statistics: { title: 'Statistics', subtitle: 'Trading statistics and analytics' },
    'qfm-analytics': { title: 'QFM Analytics', subtitle: 'Quantitative Financial Modeling metrics' },
    'backtest-lab': { title: 'Backtest Lab', subtitle: 'Strategy backtesting and optimization' },
    safety: { title: 'Safety', subtitle: 'Risk management and safety systems' },
    health: { title: 'Health', subtitle: 'System health and diagnostics' },
    'api-keys': { title: 'API Keys', subtitle: 'Exchange API key management' },
    journal: { title: 'Journal', subtitle: 'Trading journal and notes' },
    persistence: { title: 'Persistence', subtitle: 'Data backup and persistence' },
    'user-management': { title: 'User Management', subtitle: 'Manage user accounts and permissions' },
    'admin-settings': { title: 'Admin Settings', subtitle: 'Configure admin-only settings and payment address' },
    'admin-overview': { title: 'Admin Overview', subtitle: 'Core administrative metrics and system status at a glance.' },
    'admin-self-improvement': { title: 'AI Self-Improvement', subtitle: 'Advanced autonomous optimization and predictive analytics.' },
    'admin-ribs': { title: 'RIBS Evolution', subtitle: 'Advanced AI evolution, adaptation, and autonomous learning.' },
    'ribs-dashboard': { title: 'RIBS Evolution', subtitle: 'Quality Diversity Optimization for trading strategies using RIBS.' },
  };

  navItems.forEach((item) => {
    item.addEventListener('click', (event) => {
      event.preventDefault();
      navItems.forEach((nav) => nav.classList.remove('active'));
      item.classList.add('active');

      pageSections.forEach((section) => section.classList.remove('active'));
      const pageId = item.getAttribute('data-page');
      const targetSection = document.getElementById(pageId);

      if (targetSection) {
        targetSection.classList.add('active');
        if (pageInfo[pageId]) {
          pageTitle.textContent = pageInfo[pageId].title;
          pageSubtitle.textContent = pageInfo[pageId].subtitle;
        }

        // Dispatch page visibility events
        if (pageId === 'user-management') {
          window.dispatchEvent(new CustomEvent('dashboard:user-management-visible'));
        }
        if (pageId === 'admin-overview') {
          window.dispatchEvent(new CustomEvent('dashboard:admin-overview-visible'));
        }
        if (pageId === 'admin-self-improvement') {
          window.dispatchEvent(new CustomEvent('dashboard:admin-self-improvement-visible'));
        }
        if (pageId === 'admin-ribs') {
          window.dispatchEvent(new CustomEvent('dashboard:admin-ribs-visible'));
        }
        if (pageId === 'spot') {
          window.dispatchEvent(new CustomEvent('dashboard:spot-visible'));
        }
        if (pageId === 'symbol-management') {
          window.dispatchEvent(new CustomEvent('dashboard:symbol-management-visible'));
        }
        if (pageId === 'admin-settings') {
          window.dispatchEvent(new CustomEvent('dashboard:admin-settings-visible'));
        }
        if (pageId === 'api-keys') {
          window.dispatchEvent(new CustomEvent('dashboard:api-keys-visible'));
        }
        if (pageId === 'backtest-lab') {
          window.dispatchEvent(new CustomEvent('dashboard:backtest-lab-visible'));
        }
        if (pageId === 'crt-signals') {
          window.dispatchEvent(new CustomEvent('dashboard:crt-signals-visible'));
        }
        if (pageId === 'health') {
          window.dispatchEvent(new CustomEvent('dashboard:health-visible'));
        }
        if (pageId === 'market-data') {
          window.dispatchEvent(new CustomEvent('dashboard:market-data-visible'));
        }
        if (pageId === 'qfm-analytics') {
          window.dispatchEvent(new CustomEvent('dashboard:qfm-analytics-visible'));
        }
        if (pageId === 'strategies') {
          window.dispatchEvent(new CustomEvent('dashboard:strategies-visible'));
        }
        if (pageId === 'trade-history') {
          window.dispatchEvent(new CustomEvent('dashboard:trade-history-visible'));
        }
        if (pageId === 'futures') {
          window.dispatchEvent(new CustomEvent('dashboard:futures-visible'));
        }
      }
    });
  });
}

export function toggleSidebar() {
  const sidebar = document.querySelector('.sidebar');
  if (sidebar) {
    sidebar.classList.toggle('open');
  }
}

// Make toggleSidebar available globally
if (typeof window !== 'undefined') {
  window.toggleSidebar = toggleSidebar;
}
