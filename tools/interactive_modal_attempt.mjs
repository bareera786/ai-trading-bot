import { chromium, devices } from 'playwright';

async function runOnce(url, contextOptions, screenshotPath) {
  const browser = await chromium.launch();
  const context = await browser.newContext(contextOptions);
  const page = await context.newPage();

  const consoleMessages = [];
  const failedRequests = [];
  const responses = [];

  page.on('console', msg => consoleMessages.push({ type: msg.type(), text: msg.text() }));
  page.on('requestfailed', req => failedRequests.push({ url: req.url(), failureText: req.failure()?.errorText }));
  page.on('response', resp => responses.push({ url: resp.url(), status: resp.status() }));

  await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(1000);

  // Ensure rows present
  await page.waitForSelector('table tr', { timeout: 10000 }).catch(() => {});

  // Try multiple strategies to open modal
  let modalOpened = false;
  const modalSelectors = ['.trade-modal', '#trade-details-modal', '.modal', '[role="dialog"]', '.details-modal'];

  // strategy functions
  const strategies = [
    async () => {
      // click row
      const firstRow = await page.$('table tr');
      if (firstRow) {
        await firstRow.click({ timeout: 2000 }).catch(() => {});
        await page.waitForTimeout(500);
      }
    },
    async () => {
      // click details button
      const btn = await page.$('button.details-btn');
      if (btn) {
        await btn.click({ timeout: 2000 }).catch(() => {});
        await page.waitForTimeout(500);
      }
    },
    async () => {
      // try click a button with text 'Details'
      const btn = await page.$("text=Details");
      if (btn) {
        await btn.click({ timeout: 2000 }).catch(() => {});
        await page.waitForTimeout(500);
      }
    },
    async () => {
      // dispatch mouse events at center of the first row
      const firstRow = await page.$('table tr');
      if (firstRow) {
        const box = await firstRow.boundingBox();
        if (box) {
          await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
          await page.mouse.down();
          await page.mouse.up();
          await page.waitForTimeout(500);
        }
      }
    },
    async () => {
      // attempt to call a known global helper if present
      await page.evaluate(() => {
        try {
          if (window.__TEST_OPEN_TRADE_MODAL) {
            window.__TEST_OPEN_TRADE_MODAL();
            return true;
          }
        } catch (e) {}
        return false;
      }).catch(() => {});
      await page.waitForTimeout(500);
    },
  ];

  for (const s of strategies) {
    await s();
    for (const sel of modalSelectors) {
      const el = await page.$(sel);
      if (el) {
        try {
          const visible = await page.$eval(sel, el => getComputedStyle(el).display !== 'none');
          if (visible) modalOpened = true;
        } catch (e) {}
      }
    }
    if (modalOpened) break;
  }

  // final attempt: search for element that looks like modal content added after click
  const possibleModal = await page.$('div[aria-hidden="false"], div[role="dialog"]:visible').catch(() => null);
  if (possibleModal) modalOpened = true;

  // take screenshot after attempts
  await page.screenshot({ path: screenshotPath, fullPage: true }).catch(() => {});

  await browser.close();

  return { modalOpened, consoleMessages, failedRequests: failedRequests.slice(0,200), responses: responses.slice(0,200) };
}

(async () => {
  const url = process.argv[2] || 'http://151.243.171.80:5000/dashboard/trade-history';
  const desktopOut = await runOnce(url, { viewport: { width: 1366, height: 768 } }, 'artifacts/after_click_desktop.png');
  const mobileOut = await runOnce(url, devices['iPhone 12'], 'artifacts/after_click_mobile.png');
  console.log(JSON.stringify({ desktopOut, mobileOut }, null, 2));
})();
