export function initNavigation() {
  const navItems = document.querySelectorAll('.nav-item');
  const pageSections = document.querySelectorAll('.page-section');
  const pageTitle = document.getElementById('page-title');
  const pageSubtitle = document.getElementById('page-subtitle');

  const pageInfo = {
    dashboard: { title: 'Dashboard', subtitle: 'Overview of your trading bot performance' },
    'market-data': { title: 'Market Data', subtitle: 'Real-time market data and AI signals' },
    symbols: { title: 'Symbols', subtitle: 'Manage trading symbols and models' },
    spot: { title: 'Spot Trading', subtitle: 'Spot trading management and positions' },
    futures: { title: 'Futures', subtitle: 'Futures trading management' },
    strategies: { title: 'Strategies', subtitle: 'Trading strategy management and performance' },
    'crt-signals': { title: 'CRT Signals', subtitle: 'CRT signal analysis and predictions' },
    'trade-history': { title: 'Trade History', subtitle: 'Historical trading performance' },
    statistics: { title: 'Statistics', subtitle: 'Trading statistics and analytics' },
    'qfm-analytics': { title: 'QFM Analytics', subtitle: 'Quantitative Financial Modeling metrics' },
    'backtest-lab': { title: 'Backtest Lab', subtitle: 'Strategy backtesting and optimization' },
    'ml-telemetry': { title: 'ML Telemetry', subtitle: 'Machine learning model metrics' },
    safety: { title: 'Safety', subtitle: 'Risk management and safety systems' },
    health: { title: 'Health', subtitle: 'System health and diagnostics' },
    'api-keys': { title: 'API Keys', subtitle: 'Exchange API key management' },
    journal: { title: 'Journal', subtitle: 'Trading journal and notes' },
    persistence: { title: 'Persistence', subtitle: 'Data backup and persistence' },
    'user-management': { title: 'User Management', subtitle: 'Manage user accounts and permissions' },
    'admin-settings': { title: 'Admin Settings', subtitle: 'Configure admin-only settings and payment address' },
    'admin-dashboard': { title: 'Admin Dashboard', subtitle: 'Industrial-grade overview and controls for administrators.' },
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
        
        // Scroll to top when switching pages
        window.scrollTo({ top: 0, behavior: 'smooth' });
        
        if (pageId === 'user-management') {
          window.dispatchEvent(new CustomEvent('dashboard:user-management-visible'));
        }
        if (pageId === 'spot') {
          window.dispatchEvent(new CustomEvent('dashboard:spot-visible'));
        }
        if (pageId === 'symbols') {
          window.dispatchEvent(new CustomEvent('dashboard:symbols-visible'));
        }
        if (pageId === 'admin-settings') {
          window.dispatchEvent(new CustomEvent('dashboard:admin-settings-visible'));
        }
        if (pageId === 'backtest-lab') {
          window.dispatchEvent(new CustomEvent('dashboard:backtest-lab-visible'));
        }
        if (pageId === 'crt-signals') {
          window.dispatchEvent(new CustomEvent('dashboard:crt-signals-visible'));
        }
      }
    });
  });
}
