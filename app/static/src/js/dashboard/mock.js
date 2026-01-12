/* Lightweight mock data used as a safe fallback when API calls fail. This file is read-only data for the frontend and does not touch backend logic. */
export const MOCK_STATUS = {
  portfolio: {
    total_balance: 124312.45,
    unrealized_pnl: 432.12,
    open_positions: { p1: true, p2: true },
  },
  performance: { win_rate: 0.64 },
  system_status: { trading_enabled: true, models_loaded: true }
}

export const MOCK_PORTFOLIO = {
  summary: {
    total_value: 124312.45,
    total_positions: 3,
    total_pnl: 432.12
  },
  positions: [
    { id: 'p1', symbol: 'BTC/USDT', size: 0.5, entry_price: 48000, mark_price: 52500, pnl: 2250, side: 'LONG' },
    { id: 'p2', symbol: 'ETH/USDT', size: 2, entry_price: 3000, mark_price: 3200, pnl: 400, side: 'LONG' },
    { id: 'p3', symbol: 'SOL/USDT', size: 50, entry_price: 20, mark_price: 19.5, pnl: -25, side: 'SHORT' }
  ]
}

export const MOCK_TRADES = [
  { id: 't1', timestamp: Math.floor(Date.now() / 1000) - 3600, symbol: 'BTC/USDT', side: 'BUY', quantity: 0.1, price: 52000, status: 'filled', entry_price: 52000, exit_price: 52500 },
  { id: 't2', timestamp: Math.floor(Date.now() / 1000) - 3600 * 6, symbol: 'ETH/USDT', side: 'SELL', quantity: 1, price: 3100, status: 'filled', entry_price: 3200, exit_price: 3100 },
  { id: 't3', timestamp: Math.floor(Date.now() / 1000) - 3600 * 24, symbol: 'SOL/USDT', side: 'BUY', quantity: 10, price: 19.8, status: 'open', entry_price: 19.8 }
]

export const MOCK_PERF_SERIES = {
  labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'],
  values: [10000, 10500, 10200, 10800, 10600, 11000, 11432]
}
