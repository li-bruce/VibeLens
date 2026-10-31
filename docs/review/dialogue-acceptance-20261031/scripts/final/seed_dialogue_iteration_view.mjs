/** Seed an actual personal view before an ordinary coding iteration. */
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {mkdir, writeFile} from 'node:fs/promises';
import path from 'node:path';

const {chromium} = createRequire(import.meta.url)('playwright');
const base = process.argv[2], phase = process.argv[3];
const out = path.resolve('docs/review/dialogue-acceptance-20261031/iteration', phase);
await mkdir(out, {recursive: true});
const browser = await chromium.launch({headless: true, executablePath: process.env.BO_BROWSER_EXECUTABLE});
const page = await browser.newPage({viewport: {width: 1520, height: 1060}});
const result = {base, phase, errors: []};
page.on('pageerror', error => result.errors.push(String(error.stack)));
const ready = () => page.waitForFunction(() => window.graphDebug?.graph && !graphDebug.layoutBusy);
const preferences = async () => (await fetch(base + '/api/preferences')).json();
async function select(id) {
  await page.fill('#node-search', id); await page.press('#node-search', 'Enter');
  await page.waitForFunction(value => graphDebug.graph.byId.has(value), id);
  await page.fill('#node-search', '');
  await page.locator(`#semantic [data-node-id="${id}"]`).evaluate(element => element.click());
}
try {
  await page.goto(base + '/graph?lang=en'); await ready();
  if (await page.locator('#layered-toggle').innerText() === '3D') await page.click('#layered-toggle');
  await page.selectOption('#analysis-view', 'overview'); await ready();
  await page.click('#show-all'); await ready();
  await page.click('#filter-toggle');
  const allowedNodes = ['business', 'state', 'data', 'function'];
  const allowedEdges = ['flow', 'transition', 'data', 'contains', 'call'];
  for (const [kind, allowed] of [['nodes', allowedNodes], ['edges', allowedEdges], ['regions', allowedNodes]]) {
    const values = await page.locator(`#filter-${kind} input`).evaluateAll(items => items.map(item => item.value));
    for (const value of values) await page.locator(`#filter-${kind} input[value="${value}"]`).setChecked(allowed.includes(value));
  }
  await page.fill('#custom-view-name', 'Review and recipient access');
  await page.locator('#save-view button[type="submit"]').click(); await ready();
  result.selectedView = await page.inputValue('#analysis-view');
  assert.ok(result.selectedView.startsWith('custom-'));
  if (await page.locator('#filter-panel').isVisible()) await page.click('#close-filters');
  await select('logout'); await page.locator('#viewport').focus(); await page.keyboard.press('Delete');
  assert.equal(await page.locator('#semantic [data-node-id="logout"]').count(), 0);
  await select('share'); await page.locator('#viewport').focus(); await page.keyboard.press('Enter'); await ready();
  assert.equal(await page.locator('#semantic [data-node-id="share"]').getAttribute('aria-expanded'), 'true');
  const edge = await page.evaluate(() => {
    const item = graphDebug.presentation.edges.find(value => value.from === 'upload' && value.to === 'share');
    return item && {id: item.id, from: item.from, to: item.to, type: item.type, members: item.members};
  });
  assert.ok(edge, 'The unchanged upload-to-share relation is absent');
  result.hiddenRelation = edge;
  await page.locator(`#semantic-edges [data-edge-id="${edge.id}"]`).evaluate(element => element.click());
  await page.locator('#viewport').focus(); await page.keyboard.press('Shift+F10');
  await page.click('#edge-hide'); await ready();
  assert.equal(await page.locator(`#semantic-edges [data-edge-id="${edge.id}"]`).count(), 0);
  await select('download');
  const start = await page.evaluate(() => {
    const node = graphDebug.graph.byId.get('download'), camera = graphDebug.camera;
    const canvas = document.querySelector('#viewport canvas').getBoundingClientRect();
    return {x: node.x, y: node.y, pointer: {x: canvas.x + camera.pan.x + (node.x + node.w / 2) * camera.scale,
      y: canvas.y + camera.pan.y + (node.y + 31) * camera.scale}};
  });
  await page.mouse.move(start.pointer.x, start.pointer.y); await page.mouse.down();
  await page.mouse.move(start.pointer.x + 48, start.pointer.y + 24, {steps: 12}); await page.mouse.up(); await ready();
  result.pinnedNode = await page.evaluate(() => {const node = graphDebug.graph.byId.get('download'); return {id: node.id, x: node.x, y: node.y};});
  assert.ok(Math.hypot(result.pinnedNode.x - start.x, result.pinnedNode.y - start.y) > 1);
  await page.waitForFunction(async expected => {
    const document = await (await fetch('/api/preferences')).json();
    return Object.entries(document.entries).some(([key, raw]) => {
      try { const value = JSON.parse(raw); return key.endsWith(':view:' + expected.view) && value.positions?.download?.x === expected.x && value.positions.download.y === expected.y && value.filters?.hiddenNodes.includes('logout') && value.expanded.includes('share'); }
      catch { return false; }
    });
  }, {view: result.selectedView, x: result.pinnedNode.x, y: result.pinnedNode.y});
  await page.reload(); await ready();
  assert.equal(await page.inputValue('#analysis-view'), result.selectedView);
  assert.equal(await page.locator('#semantic [data-node-id="logout"]').count(), 0);
  assert.equal(await page.locator('#semantic [data-node-id="share"]').getAttribute('aria-expanded'), 'true');
  const restored = await page.evaluate(() => {const node = graphDebug.graph.byId.get('download'); return {id: node.id, x: node.x, y: node.y};});
  assert.deepEqual(restored, result.pinnedNode);
  result.preferences = await preferences();
  result.viewState = Object.entries(result.preferences.entries).filter(([key]) => key.endsWith(':view:' + result.selectedView)).map(([key, raw]) => ({key, value: JSON.parse(raw)}))[0];
  assert.ok(result.viewState.value.filters.hiddenEdges.length);
  assert.ok(result.viewState.value.annotations.download?.note);
  result.passed = !result.errors.length;
  await page.screenshot({path: path.join(out, 'saved-view-before-iteration.png')});
} catch (error) {
  result.passed = false; result.error = String(error.stack);
  await page.screenshot({path: path.join(out, 'saved-view-failure.png')}).catch(() => {});
} finally {
  await writeFile(path.join(out, 'saved-view.json'), JSON.stringify(result, null, 2));
  await browser.close();
}
console.log(JSON.stringify({passed: result.passed, view: result.selectedView, error: result.error}));
if (!result.passed) process.exitCode = 1;
