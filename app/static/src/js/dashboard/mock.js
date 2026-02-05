/* Lightweight mock data used as a safe fallback when API calls fail. This file is read-only data for the frontend and does not touch backend logic. */
export const MOCK_STATUS = {
  portfolio: {
    total_balance: 124312.45,
    unrealized_pnl: 432.12,
    open_positions: { p1: true, p2: true },
  },
  performance: { win_rate: 0.64 },
  system_status: { trading_enabled: true, futures_trading_enabled: false, models_loaded: true }
}

export const MOCK_PORTFOLIO = {
  summary: {
    total_value: 124312.45,
    total_positions: 3,
    total_pnl: 432.12
  },
  positions: [
    { id: 'p1', symbol: 'BTC/USDT', size: 0.5, entry_price: 94000, mark_price: 95200, pnl: 600, side: 'LONG' },
    { id: 'p2', symbol: 'ETH/USDT', size: 2, entry_price: 3150, mark_price: 3200, pnl: 100, side: 'LONG' },
    { id: 'p3', symbol: 'SOL/USDT', size: 50, entry_price: 205, mark_price: 210.5, pnl: 275, side: 'LONG' }
  ]
}

export const MOCK_TRADES = [
  { id: 't1', timestamp: Math.floor(Date.now() / 1000) - 3600, symbol: 'BTC/USDT', side: 'BUY', quantity: 0.1, price: 95000, status: 'filled', entry_price: 95000, exit_price: 95500, pnl: 50.00 },
  { id: 't2', timestamp: Math.floor(Date.now() / 1000) - 3600 * 6, symbol: 'ETH/USDT', side: 'SELL', quantity: 1, price: 3200, status: 'filled', entry_price: 3300, exit_price: 3200, pnl: 100.00 },
  { id: 't3', timestamp: Math.floor(Date.now() / 1000) - 3600 * 24, symbol: 'SOL/USDT', side: 'BUY', quantity: 10, price: 210.50, status: 'open', entry_price: 210.50, pnl: null }
]

export const MOCK_PERF_SERIES = {
  labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'],
  values: [10000, 10500, 10200, 10800, 10600, 11000, 11432]
}
