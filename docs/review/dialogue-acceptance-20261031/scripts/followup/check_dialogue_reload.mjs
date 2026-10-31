/** Diagnose actual reload requests without changing the viewer or its deadlines. */
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

const { chromium } = createRequire(import.meta.url)('playwright');
const base = process.argv[2];
const out = path.resolve('docs/review/dialogue-acceptance-20261031', process.argv[3]);
await mkdir(out, { recursive: true });
const browser = await chromium.launch({headless: true, executablePath: process.env.BO_BROWSER_EXECUTABLE});
const page = await browser.newPage({viewport: {width: 1520, height: 1060}});
const requests = [], failures = [], reloads = [];
const active = new Map();
page.on('request', request => {
  const entry = {path: new URL(request.url()).pathname, start: Date.now()};
  active.set(request, entry); requests.push(entry);
});
page.on('requestfinished', request => {
  const item = active.get(request);
  if (item) item.duration_ms = Date.now() - item.start;
  active.delete(request);
});
page.on('requestfailed', request => {
  const item = active.get(request);
  if (item) {item.duration_ms = Date.now() - item.start; item.error = request.failure()?.errorText;}
  failures.push({path: new URL(request.url()).pathname, error: request.failure()?.errorText});
  active.delete(request);
});
try {
  await page.goto(base + '/graph?lang=en');
  await page.waitForFunction(() => window.graphDebug?.graph?.boxes && !graphDebug.layoutBusy);
  for (let index = 0; index < 12; index++) {
    const lang = index % 2 ? 'en' : 'zh-CN';
    const started = Date.now();
    await page.selectOption('#language', lang);
    await page.waitForURL(url => url.searchParams.get('lang') === lang);
    await page.waitForFunction(() => window.graphDebug?.graph?.boxes && !graphDebug.layoutBusy);
    reloads.push({index, lang, duration_ms: Date.now() - started});
  }
  assert.equal(reloads.length, 12);
} catch (error) {
  failures.push({case: 'actual language reload', error: String(error.stack)});
  await page.screenshot({path: path.join(out, 'failure.png'), fullPage: true});
} finally {
  await writeFile(path.join(out, 'reload-results.json'), JSON.stringify({passed: !failures.length, base,
    reloads, failures, pending: [...active.values()], requests}, null, 2));
  await browser.close();
}
console.log(JSON.stringify({reloads: reloads.length, failures}));
if (failures.length) process.exitCode = 1;
