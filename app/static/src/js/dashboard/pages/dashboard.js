import { fetchJson } from '../utils/network.js'
import { MOCK_STATUS, MOCK_PORTFOLIO, MOCK_TRADES, MOCK_PERF_SERIES } from '../mock.js'

/*
  Modernized dashboard script: mobile-first enhancements, graceful fallbacks,
  responsive mobile-card render for recent trades, improved dedupe and PnL,
  and accessible updates. Preserves existing function names and endpoints
  so backend integrations remain unchanged.
*/

let performanceChart = null

export async function refreshDashboardCards() {
  // Try API, fall back to mock data when necessary
  const data = await safeFetch('/api/status', MOCK_STATUS)
  if (!data) return

  // PORTFOLIO total value + unrealized pnl
  const portfolioCard = document.querySelector('#dashboard .dashboard-card:nth-child(1) .card-value')
  if (portfolioCard && (data.portfolio || data.portfolio === null)) {
    const portfolio = data.portfolio || {}
    const totalValue = (portfolio.total_balance || 0) + (portfolio.unrealized_pnl || 0)
    portfolioCard.textContent = formatCurrency(totalValue)
  }

  // OPEN POSITIONS
  const tradesCard = document.querySelector('#dashboard .dashboard-card:nth-child(2) .card-value')
  if (tradesCard && (data.portfolio || data.portfolio === null)) {
    const openPositions = data.portfolio && data.portfolio.open_positions ? Object.keys(data.portfolio.open_positions).length : 0
    tradesCard.textContent = openPositions
  }

  // WIN RATE
  const winRateCard = document.querySelector('#dashboard .dashboard-card:nth-child(3) .card-value')
  if (winRateCard && (data.performance || data.performance === null)) {
    const winRate = data.performance ? (data.performance.win_rate || 0) : 0
    winRateCard.textContent = `${(winRate * 100).toFixed(1)}%`
  }

  // System status indicator (online/offline)
  const systemCard = document.querySelector('#dashboard .dashboard-card:nth-child(4) .card-value .status-indicator')
  if (systemCard && (data.system_status || data.system_status === null)) {
    const sys = data.system_status || {}
    const isOnline = !!(sys.trading_enabled && sys.models_loaded)
    systemCard.className = `status-indicator ${isOnline ? 'status-success' : 'status-warning'}`
    systemCard.textContent = isOnline ? 'ONLINE' : 'OFFLINE'
  }

  // load user-specific widgets and chart (non-blocking)
  await loadUserDashboardData()
  await updatePerformanceChart()
}

// Helper: try API but return fallback data on error or timeout
async function safeFetch(url, fallback, timeoutMs = 3000) {
  try {
    const controller = new AbortController()
    const id = setTimeout(() => controller.abort(), timeoutMs)
    const res = await fetchJson(url, { signal: controller.signal })
    clearTimeout(id)
    if (!res || res.error) return fallback
    return res
  } catch (err) {
    // network error or abort -> use fallback so UI remains responsive
    return fallback
  }
}

async function updatePerformanceChart() {
  if (typeof Chart === 'undefined') return
  const ctx = document.getElementById('performance-chart')
  if (!ctx) return

  // Prefer server data but fallback to mock series if unavailable
  const data = await safeFetch('/api/performance_chart', MOCK_PERF_SERIES)
  const labels = (data && data.labels) || (data.chart_data && data.chart_data.labels) || MOCK_PERF_SERIES.labels
  const values = (data && data.values) || (data.chart_data && data.chart_data.values) || MOCK_PERF_SERIES.values

  const dataset = {
    label: 'Portfolio Value',
    data: values,
    borderColor: getComputedStyle(document.documentElement).getPropertyValue('--primary') || '#3b82f6',
    backgroundColor: 'rgba(124,58,237,0.08)',
    tension: 0.35,
    pointRadius: 0
  }

  if (!performanceChart) {
    performanceChart = new Chart(ctx, {
      type: 'line',
      data: { labels, datasets: [dataset] },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { mode: 'index', intersect: false } },
        scales: {
          x: { grid: { display: false } },
          y: { grid: { color: 'rgba(2,6,23,0.04)' }, ticks: { callback: v => '$' + Number(v).toLocaleString() } }
        }
      }
    })
  } else {
    performanceChart.data.labels = labels
    performanceChart.data.datasets[0].data = values
    performanceChart.update()
  }
}

// Sort helper (desc by timestamp)
function sortTradesByTimestamp(trades) {
  return trades.slice().sort((a, b) => (new Date(b.opened_at || 0) - new Date(a.opened_at || 0)))
}

export async function refreshRecentActivity() {
  const user = await safeFetch('/api/current_user', { is_admin: false })
  const mergeParam = user && user.is_admin ? '&merge_db=1' : ''
  const data = await safeFetch(`/api/trades?page=1&limit=10${mergeParam}`, { trades: MOCK_TRADES })
  if (!data || data.error || !Array.isArray(data.trades)) return

  const container = document.getElementById('recent-activity-container') || document.getElementById('recent-activity')
  if (!container) return

  // Always sort and show up to 5 recent items
  const sortedTrades = sortTradesByTimestamp(data.trades || [])
  renderRecentActivity(sortedTrades.slice(0, 5))
}

function renderRecentActivity(trades) {
  // The page may contain a table body (#recent-activity) and/or a mobile list placeholder (#recent-activity-mobile).
  const tableBody = document.getElementById('recent-activity')
  const mobileList = document.getElementById('recent-activity-mobile')

  if (tableBody) tableBody.innerHTML = ''
  if (mobileList) mobileList.innerHTML = ''

  trades.forEach((trade) => {
    // Use canonical schema: opened_at for timestamp
    const ts = new Date(trade.opened_at || Date.now())
    const timeString = isNaN(ts.getTime()) ? '—' : ts.toLocaleTimeString('en-US', { hour12: false })
    const statusClass = trade.status === 'CLOSED' ? 'status-success' : 'status-warning'
    const rowHtml = `
      <tr class="dashboard-row">
        <td class="px-2 py-2 text-sm">${timeString}</td>
        <td class="px-2 py-2 text-sm">${escapeHtml(trade.symbol || 'N/A')}</td>
        <td class="px-2 py-2 text-sm">${escapeHtml(trade.side || 'N/A')}</td>
        <td class="px-2 py-2 text-sm">$${(trade.entry_price || 0).toFixed(2)}</td>
        <td class="px-2 py-2 text-sm"><span class="status-indicator ${statusClass}">${escapeHtml(trade.status || 'unknown')}</span></td>
      </tr>
    `
    if (tableBody) tableBody.insertAdjacentHTML('beforeend', rowHtml)

    // Mobile card version (if mobile placeholder exists we render a compact card)
    if (mobileList) {
      const cardHtml = `
        <div class="mobile-trade-card p-3 mb-3 card">
          <div class="flex justify-between items-start">
            <div>
              <div class="text-sm font-medium">${escapeHtml(trade.symbol || 'N/A')}</div>
              <div class="text-xs text-slate-500">${timeString} • ${escapeHtml(trade.side || '')}</div>
            </div>
            <div class="text-right">
              <div class="text-sm">$${(trade.entry_price || 0).toFixed(2)}</div>
              <div class="text-xs ${trade.status === 'CLOSED' ? 'text-emerald-600' : 'text-amber-600'}">${escapeHtml(trade.status || '')}</div>
            </div>
          </div>
        </div>
      `
      mobileList.insertAdjacentHTML('beforeend', cardHtml)
    }
  })
}

// Load portfolio and trades for logged-in user; if API not available, use mock data so UI stays usable
async function loadUserDashboardData() {
  const user = await safeFetch('/api/current_user', { id: null })
  const portfolio = user && user.id ? await safeFetch(`/api/portfolio/user/${user.id}`, MOCK_PORTFOLIO) : MOCK_PORTFOLIO
  if (portfolio) updateUserPortfolioWidgets(portfolio)

  const tradesRes = await safeFetch('/api/trades?limit=10', { trades: MOCK_TRADES })
  if (tradesRes && Array.isArray(tradesRes.trades)) updateUserTradesTable(tradesRes.trades)
}

function updateUserPortfolioWidgets(portfolio) {
  const summary = portfolio.summary || {}
  const totalValue = summary.total_value || 0
  const totalPositions = summary.total_positions || 0
  const totalPnl = summary.total_pnl || 0

  setIfExists('#user-portfolio-value', formatCurrency(totalValue))
  setIfExists('#user-portfolio-status', `${totalPositions} active position${totalPositions === 1 ? '' : 's'}`)

  const pnlElement = document.getElementById('user-total-pnl')
  if (pnlElement) {
    const isPositive = totalPnl >= 0
    pnlElement.textContent = `${isPositive ? '+' : ''}${formatCurrency(Math.abs(totalPnl))}`
    pnlElement.className = isPositive ? 'text-success' : 'text-danger'
  }

  const riskLevelElement = document.getElementById('user-risk-level')
  if (riskLevelElement) {
    let riskLevel = 'LOW'
    let riskClass = 'status-success'
    if (totalPositions > 5) { riskLevel = 'MEDIUM'; riskClass = 'status-warning' }
    if (totalPositions > 10) { riskLevel = 'HIGH'; riskClass = 'status-danger' }
    riskLevelElement.textContent = riskLevel
    riskLevelElement.className = `status-indicator ${riskClass}`
  }

  setIfExists('#user-risk-details', `${totalPositions} position${totalPositions === 1 ? '' : 's'} open` )
}

function removeDuplicateTrades(trades) {
  // Deduplicate by id when available, otherwise by stable key of symbol/side/timestamp/price/quantity
  const map = new Map()
  trades.forEach(trade => {
    const key = trade.id || `${trade.symbol}|${trade.side}|${trade.timestamp}|${trade.price}|${trade.quantity}`
    if (!map.has(key)) map.set(key, trade)
  })
  return Array.from(map.values())
}

function calculatePnL(trade) {
  // Handles BUY vs SELL, supports entry/exit/executed fields. Returns a numeric pnl amount.
  const entry = Number(trade.entry_price ?? trade.entry ?? trade.executed_entry ?? 0)
  const exit = Number(trade.exit_price ?? trade.exit ?? trade.executed_exit ?? trade.price ?? 0)
  const qty = Number(trade.quantity ?? trade.qty ?? 0)
  if (!qty) return 0
  if ((trade.side || '').toUpperCase() === 'BUY') return (exit - entry) * qty
  if ((trade.side || '').toUpperCase() === 'SELL') return (entry - exit) * qty
  return 0
}

function updateUserTradesTable(trades) {
  // Accepts an array of trades, dedupes, sorts, and renders both table (desktop) and mobile card list (if placeholder exists).
  const tbody = document.getElementById('user-recent-trades')
  const mobilePlaceholder = document.getElementById('user-recent-trades-mobile')

  if ((!tbody) && (!mobilePlaceholder)) return
  if (!Array.isArray(trades) || trades.length === 0) {
    if (tbody) tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--text-secondary)">No recent trades</td></tr>'
    if (mobilePlaceholder) mobilePlaceholder.innerHTML = '<div class="text-sm text-slate-500">No recent trades</div>'
    return
  }

  const unique = removeDuplicateTrades(trades)
  const sorted = sortTradesByTimestamp(unique)

  if (tbody) tbody.innerHTML = ''
  if (mobilePlaceholder) mobilePlaceholder.innerHTML = ''

  sorted.slice(0, 20).forEach(trade => {
    // Use canonical schema: PnL is provided by backend, null for OPEN trades
    const pnl = trade.pnl  // No client-side calculation
    const isOpen = trade.status === 'OPEN'
    const statusClass = trade.status === 'CLOSED' ? 'status-success' : 'status-warning'
    const pnlClass = pnl && pnl >= 0 ? 'text-success' : 'text-danger'
    // Use opened_at from canonical schema
    const ts = new Date(trade.opened_at || Date.now())
    const dateString = isNaN(ts.getTime()) ? '—' : ts.toLocaleDateString('en-US')

    if (tbody) {
      const row = document.createElement('tr')
      row.className = 'hover:bg-slate-50'
      row.innerHTML = `
        <td class="px-3 py-2 text-sm">${dateString}</td>
        <td class="px-3 py-2 text-sm">${escapeHtml(trade.symbol || 'N/A')}</td>
        <td class="px-3 py-2 text-sm">${escapeHtml(trade.side || 'N/A')}</td>
        <td class="px-3 py-2 text-sm">${escapeHtml(String(trade.quantity || 0))}</td>
        <td class="px-3 py-2 text-sm">$${(Number(trade.entry_price || 0)).toFixed(4)}</td>
        <td class="px-3 py-2 text-sm ${pnlClass}">${isOpen || pnl === null ? '—' : (pnl >= 0 ? '+' : '-') + '$' + Math.abs(pnl).toFixed(2)}</td>
        <td class="px-3 py-2 text-sm"><span class="status-indicator ${statusClass}">${escapeHtml(trade.status || 'OPEN')}</span></td>
      `

      // details cell with disabled state for incomplete trades (keeps UI consistent)
      const detailsCell = document.createElement('td')
      const detailsBtn = document.createElement('button')
      detailsBtn.className = 'btn btn-sm btn-primary'
      detailsBtn.textContent = 'Details'
      detailsBtn.disabled = isOpen
      if (isOpen) detailsBtn.title = 'Trade open - details unavailable'
      detailsBtn.addEventListener('click', () => openTradeModal(trade))
      detailsCell.appendChild(detailsBtn)
      row.appendChild(detailsCell)

      tbody.appendChild(row)
    }

    if (mobilePlaceholder) {
      const card = document.createElement('div')
      card.className = 'mobile-card p-3 mb-3 card'
      card.innerHTML = `
        <div class=\"flex justify-between items-start\">\n          <div>\n            <div class=\"font-medium\">${escapeHtml(trade.symbol || 'N/A')}</div>\n            <div class=\"text-xs text-slate-500\">${dateString} • ${escapeHtml(trade.side || '')}</div>\n          </div>\n          <div class=\"text-right\">\n            <div class=\"text-sm\">$${(Number(trade.entry_price || 0)).toFixed(2)}</div>\n            <div class=\"text-xs ${trade.status === 'CLOSED' ? 'text-emerald-600' : 'text-amber-600'}\">${escapeHtml(trade.status || '')}</div>\n          </div>\n        </div>\n        <div class=\"mt-2 flex items-center justify-between\">\n          <div class=\"text-sm ${pnl && pnl >= 0 ? 'text-emerald-600' : 'text-rose-600'}\">${isOpen || pnl === null ? '—' : (pnl >= 0 ? '+' : '-') + '$' + Math.abs(pnl).toFixed(2)}</div>\n          <div><button class=\"btn btn-xs btn-outline\" ${isOpen ? 'disabled' : ''}>Details</button></div>\n        </div>\n      `
      mobilePlaceholder.appendChild(card)
    }
  })
}

// Small helper to open a modal (UI-only). If a modal element exists on the page, populate and show it.
function openTradeModal(trade) {
  try {
    const modal = document.getElementById('trade-details-modal')
    if (!modal) {
      // fallback to alert for pages that don't have modal markup
      alert(`Trade details (mock): ${trade.symbol} ${trade.side} ${trade.quantity} @ ${trade.price}`)
      return
    }
    const body = modal.querySelector('.modal-body')
    if (body) {
      body.textContent = JSON.stringify(trade, null, 2)
    }
    modal.classList.add('open')
  } catch (err) { /* silent */ }
}

function setIfExists(selector, text) {
  const el = document.querySelector(selector)
  if (el) el.textContent = text
}

function escapeHtml(s) {
  if (typeof s !== 'string') return s
  return s.replace(/[&<>\"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '\"': '&quot;', "'": '&#39;' })[c])
}

function formatCurrency(value) {
  const n = Number(value || 0)
  return '$' + n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// Expose a window-level debug render for manual UI checks (uses mock if API offline)
window.__dashboard_render_debug = async function() {
  await refreshDashboardCards()
  await refreshRecentActivity()
}

// Lightweight modal close behavior (if modal present)
document.addEventListener('click', (e) => {
  const modal = document.getElementById('trade-details-modal')
  if (!modal) return
  if (e.target.classList.contains('modal-close')) modal.classList.remove('open')
})

// Ensure mobile placeholders and a simple modal exist at runtime so the script
// remains resilient when templates don't include mobile-specific markup.
function createFallbackPlaceholders() {
  const dashboardSection = document.getElementById('dashboard') || document.body

  // recent activity mobile list
  if (!document.getElementById('recent-activity-mobile')) {
    const el = document.createElement('div')
    el.id = 'recent-activity-mobile'
    el.className = 'mobile-only'
    // place it near the recent-activity table if present
    const table = document.getElementById('recent-activity')
    if (table && table.parentElement) table.parentElement.appendChild(el)
    else dashboardSection.appendChild(el)
  }

  // user recent trades mobile placeholder
  if (!document.getElementById('user-recent-trades-mobile')) {
    const el = document.createElement('div')
    el.id = 'user-recent-trades-mobile'
    el.className = 'mobile-only'
    const table = document.getElementById('user-recent-trades')
    if (table && table.parentElement) table.parentElement.appendChild(el)
    else dashboardSection.appendChild(el)
  }

  // simple trade details modal used by openTradeModal; inserted only if absent
  if (!document.getElementById('trade-details-modal')) {
    const modal = document.createElement('div')
    modal.id = 'trade-details-modal'
    modal.className = ''
    modal.innerHTML = `
      <div class="modal-body card">
        <button class="modal-close btn btn-xs btn-outline" style="float:right">Close</button>
        <pre style="white-space:pre-wrap;word-break:break-word;">Trade details will appear here</pre>
      </div>`
    document.body.appendChild(modal)
  }
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', createFallbackPlaceholders)
else createFallbackPlaceholders()

// Export helper for other scripts to call same name as before
export { updatePerformanceChart as updatePerformanceChart }
