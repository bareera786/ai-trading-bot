import assert from 'assert';

// Provide minimal globals so importing the dashboard module in Node doesn't throw
globalThis.window = globalThis.window || {};
globalThis.document = globalThis.document || {
  getElementById: () => null,
  querySelector: () => null,
  createElement: () => ({ style: {}, appendChild: () => {}, removeChild: () => {} }),
};

// Use dynamic import so we can set up globals before the module is evaluated.
const { convertTradesToCSV } = await import('../app/static/src/js/dashboard/pages/trade-history.js');

function run() {
  // Test 1: header order and labels
  const csv = convertTradesToCSV([]);
  const lines = csv.split('\n');
  const headers = lines[0].split(',');
  const expectedHeaders = [
    'Date',
    'Symbol',
    'Type',
    'Side',
    'Quantity',
    'Entry Price',
    'Leverage',
    'Execution Mode',
    'Market Type',
    'Exchange',
    'Margin Type',
    'Reduce Only',
    'Order ID',
    'P&L',
    'Status',
  ];
  assert.deepStrictEqual(headers, expectedHeaders, 'CSV headers do not match expected order');

  // Test 2: blank P&L when missing, and formatted P&L when present
  const trades = [
    {
      timestamp: '2026-01-09T12:00:00Z',
      symbol: 'BTCUSD',
      market_type: 'FUTURES',
      exchange: 'Binance',
      execution_mode: 'futures',
      quantity: 0.5,
      entry_price: 20000,
      leverage: 10,
      // pnl missing
      status: 'filled',
      side: 'LONG',
      real_order_id: 'ord-1',
    },
    {
      timestamp: '2026-01-09T13:00:00Z',
      symbol: 'ETHUSD',
      market_type: 'SPOT',
      exchange: 'Coinbase',
      execution_mode: 'real',
      quantity: 1.25,
      entry_price: 1500,
      leverage: null,
      pnl: 12.3456,
      status: 'closed',
      side: 'SHORT',
      real_order_id: 'ord-2',
    },
  ];

  const csv2 = convertTradesToCSV(trades);
  console.log('DEBUG CSV full:\n' + csv2);
  const rows = csv2.split('\n');
  assert(rows.length >= 3, 'Expected header + 2 rows');

  function parseCsvLine(line) {
    const res = [];
    let cur = '';
    let inQuotes = false;
    for (let i = 0; i < line.length; i++) {
      const ch = line[i];
      if (ch === '"') {
        // Peek next char to handle escaped quotes
        if (inQuotes && line[i + 1] === '"') {
          cur += '"';
          i++; // skip escaped quote
        } else {
          inQuotes = !inQuotes;
        }
        continue;
      }
      if (ch === ',' && !inQuotes) {
        res.push(cur);
        cur = '';
        continue;
      }
      cur += ch;
    }
    res.push(cur);
    return res.map(s => s.trim());
  }

  const row1 = parseCsvLine(rows[1]);
  const row2 = parseCsvLine(rows[2]);

  // P&L is column index 13 (0-based). The implementation wraps the P&L value in quotes.
  console.log('DEBUG CSV parsed row1 col13:', row1[13]);
  console.log('DEBUG CSV parsed row2 col13:', row2[13]);
  assert.strictEqual(row1[13], '', 'Expected empty P&L for missing pnl');
  assert.ok(row2[13].startsWith('$') || row2[13].startsWith('-$'), 'Expected P&L starting with $ or -$ for pnl');
  assert.ok(row2[13].includes('12.3456'), 'Expected exact pnl value in CSV for second trade');

  console.log('✅ JS CSV tests passed');
}

try {
  run();
  process.exit(0);
} catch (err) {
  console.error('❌ JS CSV tests failed');
  console.error(err && err.stack ? err.stack : err);
  process.exit(1);
}
