import { chromium, devices } from 'playwright';

const url = process.argv[2];
const desktopPath = process.argv[3];
const mobilePath = process.argv[4];

if (!url || !desktopPath || !mobilePath) {
  console.error('Usage: node tools/take_screenshots.mjs <url> <desktopPath> <mobilePath>');
  process.exit(2);
}

(async () => {
  // Desktop
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1366, height: 768 } });
  const page = await context.newPage();
  await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
  await page.screenshot({ path: desktopPath, fullPage: true });
  await browser.close();

  // Mobile (iPhone 12)
  const browser2 = await chromium.launch();
  const context2 = await browser2.newContext({ ...devices['iPhone 12'] });
  const page2 = await context2.newPage();
  await page2.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
  await page2.screenshot({ path: mobilePath, fullPage: true });
  await browser2.close();

  console.log('Screenshots saved:', desktopPath, mobilePath);
})();
