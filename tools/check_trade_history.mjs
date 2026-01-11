import { chromium, devices } from 'playwright';

async function check(url, contextOptions, label) {
  const browser = await chromium.launch();
  const context = await browser.newContext(contextOptions);
  const page = await context.newPage();

  const consoleMessages = [];
  page.on('console', msg => consoleMessages.push(`${msg.type()}: ${msg.text()}`));

  await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });

  // Wait for table rows to render
  await page.waitForSelector('table tr', { timeout: 10000 }).catch(() => {});

  // Extract rows data
  const rows = await page.$$eval('table tr', trs =>
    trs.map(tr => {
      const cells = Array.from(tr.querySelectorAll('td')).map(td => td.innerText.trim());
      // find details button
      const btn = tr.querySelector('button.details-btn');
      const hasBtn = !!btn;
      const disabled = hasBtn ? btn.disabled : null;
      // Attempt to get timestamp and entry/exit
      const timestamp = tr.getAttribute('data-timestamp') || '';
      const entry = tr.querySelector('.entry-price')?.innerText?.trim() || '';
      const exit = tr.querySelector('.exit-price')?.innerText?.trim() || '';
      const pnl = tr.querySelector('.pnl')?.innerText?.trim() || '';
      return { cells, hasBtn, disabled, timestamp, entry, exit, pnl };
    })
  );

  // Check newest-first via data-timestamp if available or first cell parse
  const timestamps = rows.map(r => r.timestamp || r.cells[0] || '');
  // Try parse numeric timestamps (epoch or ISO)
  const parsed = timestamps.map(t => {
    if (!t) return null;
    const n = Number(t);
    if (!isNaN(n)) return n;
    const d = Date.parse(t);
    return isNaN(d) ? null : d;
  });

  let orderOk = true;
  for (let i = 1; i < parsed.length; i++) {
    if (parsed[i] != null && parsed[i - 1] != null && parsed[i] > parsed[i - 1]) {
      orderOk = false; // later row newer than previous => not descending
      break;
    }
  }

  // Check details button presence
  let detailsOk = true;
  let disabledCount = 0;
  let missingBtnCount = 0;
  for (const r of rows) {
    if (!r.hasBtn) missingBtnCount++;
    if (r.hasBtn && r.disabled) disabledCount++;
  }
  if (missingBtnCount > 0) detailsOk = false;

  // Try click first non-disabled row to open modal (.trade-modal), or click Details button
  let modalOpened = false;
  try {
    const modalSelectors = ['.trade-modal', '#trade-details-modal', '.modal', '[role="dialog"]', '.details-modal'];

    // 1) Click first row
    const firstRow = await page.$('table tr');
    if (firstRow) {
      await firstRow.click({ timeout: 2000 }).catch(() => {});
      for (const sel of modalSelectors) {
        const el = await page.$(sel);
        if (el) {
          const visible = await page.$eval(sel, el => getComputedStyle(el).display !== 'none');
          if (visible) modalOpened = true;
        }
      }
    }

    // 2) If not opened, try clicking the details button on first row
    if (!modalOpened) {
      const firstBtn = await page.$('button.details-btn');
      if (firstBtn) {
        await firstBtn.click({ timeout: 2000 }).catch(() => {});
        for (const sel of modalSelectors) {
          const el = await page.$(sel);
          if (el) {
            const visible = await page.$eval(sel, el => getComputedStyle(el).display !== 'none');
            if (visible) modalOpened = true;
          }
        }
      }
    }
  } catch (e) {
    modalOpened = false;
  }

  await browser.close();

  return { label, orderOk, detailsOk, missingBtnCount, disabledCount, modalOpened, consoleMessages: consoleMessages.slice(0,200) };
}

(async () => {
  const url = process.argv[2] || 'http://151.243.171.80:5000/dashboard/trade-history';
  const desktop = await check(url, { viewport: { width: 1366, height: 768 } }, 'desktop');
  const mobile = await check(url, devices['iPhone 12'], 'mobile');
  console.log(JSON.stringify({ desktop, mobile }, null, 2));
})();
