/** Inspect new waiting/resumption facts at their actual replay cursor in 2D and 3D. */
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {mkdir, readFile, writeFile} from 'node:fs/promises';
import path from 'node:path';
import {timeline} from '../skills/vibelens/assets/stategraph-viewer/recording.js';

const {chromium} = createRequire(import.meta.url)('playwright');
const base = process.argv[2], source = process.argv[3], phase = process.argv[4];
const flow = JSON.parse(await readFile(source, 'utf8'));
assert.equal(flow.passed, true, 'Only inspect an independently complete real business flow');
const out = path.resolve('docs/review/dialogue-acceptance-20261031/timeline-' + phase);
await mkdir(out, {recursive: true});
const recording = await (await fetch(base + '/api/recordings/' + flow.recordingId)).json();
const items = timeline(recording), checks = [], errors = [];
const result = {phase, base, recordingId: flow.recordingId, checks, errors};
const browser = await chromium.launch({headless: true, executablePath: process.env.BO_BROWSER_EXECUTABLE});
const page = await browser.newPage({viewport: {width: 1520, height: 1060}});
page.on('pageerror', error => errors.push(String(error.stack)));
try {
  await page.goto(base + '/graph?lang=en');
  await page.waitForFunction(() => window.graphDebug?.graph && !graphDebug.layoutBusy);
  await page.selectOption('#analysis-view', 'business');
  await page.selectOption('#record-list', flow.recordingId);
  await page.waitForSelector('#recording-timeline canvas', {state: 'visible'});
  await page.selectOption('#replay-grain', 'events');
  await page.selectOption('.trace-scope', 'all');
  const selected = ['awaiting_supplement', 'pending', 'approved'].map(state => {
    const raw = items.findIndex(item => item.phase === 'change' && item.outputs?.state === state);
    assert.ok(raw >= 0, 'A real state transition is missing: ' + state);
    return {state, raw};
  });
  for (const mode of ['2D', '3D']) {
    if (await page.locator('#layered-toggle').innerText() !== mode) await page.click('#layered-toggle');
    await page.selectOption('#analysis-view', 'states');
    for (const {state, raw} of selected) {
      await page.selectOption('#replay-events', String(raw));
      await page.waitForFunction(() => !graphDebug.layoutBusy);
      const actual = await page.evaluate(() => ({state: graphDebug.view.machine.current, timeline: graphDebug.timeline, raw: graphDebug.view.replay.index}));
      assert.equal(actual.state, state);
      assert.equal(actual.raw, raw);
      assert.equal(actual.timeline.eventId, items[raw].id);
      assert.equal(await page.locator('#recording-timeline').getAttribute('data-event-id'), items[raw].id);
      assert.equal(await page.locator('#replay-position').getAttribute('data-event-id'), items[raw].id);
      await page.click('.trace-inspect');
      const payload = JSON.parse(await page.locator('.trace-payload').innerText());
      assert.equal(payload.id, items[raw].id);
      assert.ok(payload.changes.some(change => change.kind === 'business' && change.after === state));
      await page.click('.trace-inspect');
      await page.screenshot({path: path.join(out, state + '-' + mode.toLowerCase() + '.png')});
    }
    checks.push({name: mode + ' graph and timeline share exact waiting, resumption and approval state events', states: selected.map(item => ({state: item.state, id: items[item.raw].id}))});
  }
  await page.selectOption('#analysis-view', 'business');
  await page.click('.trace-fit');
  const actual = await page.evaluate(() => graphDebug.timeline);
  const waits = actual.lifecycles.filter(item => item.node === 'awaiting_supplement');
  assert.ok(waits.length >= 4, 'The repeated waiting periods have no separate lifetimes');
  assert.ok(waits.every(item => item.duration > 0 && !item.unfinished));
  for (const node of ['return_share', 'resubmit_share']) {
    const entered = recording.events.filter(event => event.node === node && event.phase === 'enter');
    assert.ok(entered.length > 0);
    for (const event of entered) {
      const interval = actual.lifecycles.find(item => item.entryEventId === event.id);
      assert.ok(interval && !interval.unfinished, 'A real return or exception has no closed lifetime: ' + event.id);
    }
  }
  assert.ok(actual.routes.some(route => actual.rows[route.fromRow].layer !== actual.rows[route.toRow].layer));
  assert.ok(actual.routes.some(route => route.fromRow !== route.toRow && actual.rows[route.fromRow].layer === actual.rows[route.toRow].layer));
  checks.push({name: 'Repeated waiting periods and physical operation exits retain separate lifetimes and connected handoffs', waits: waits.map(item => ({id: item.id, duration: item.duration})), routes: actual.routes.length});
  await page.screenshot({path: path.join(out, 'repeated-waiting-lifetimes.png')});
  result.passed = !errors.length;
} catch (error) {
  result.passed = false; result.error = String(error.stack);
  await page.screenshot({path: path.join(out, 'failure.png')}).catch(() => {});
} finally {
  await writeFile(path.join(out, 'results.json'), JSON.stringify(result, null, 2));
  await browser.close();
}
console.log(JSON.stringify({passed: result.passed, checks: checks.length, error: result.error}));
if (!result.passed) process.exitCode = 1;
