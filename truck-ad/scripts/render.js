// Render an HTML page to PNG at its CSS size. usage: node render.js page.html out.png W H
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const [, , page, out, w, h] = process.argv;
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: +w, height: +h }, deviceScaleFactor: 1 });
  await p.goto(page.includes('://') ? page : 'file://' + path.resolve(page.split('#')[0]) + (page.includes('#') ? '#' + page.split('#')[1] : ''));
  await p.evaluate(() => document.fonts.ready);
  await p.waitForTimeout(300);
  await p.screenshot({ path: out, omitBackground: true });
  await b.close();
})();
