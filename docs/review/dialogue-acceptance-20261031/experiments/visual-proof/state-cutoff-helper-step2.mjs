/** Capture readable original waiting intervals and an actual orbit, without editing facts. */
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import {mkdir, readFile, writeFile} from 'node:fs/promises';
import path from 'node:path';

const {chromium} = createRequire(import.meta.url)('playwright');
const base = process.argv[2], phase = process.argv[3];
const flow = JSON.parse(await readFile(`docs/review/dialogue-acceptance-20261031/operations-${phase}/results.json`, 'utf8'));
assert.equal(flow.passed, true);
const out = path.resolve(`docs/review/dialogue-acceptance-20261031/timeline-${phase}`);
await mkdir(out, {recursive: true});
const original = await (await fetch(base + '/api/recordings/' + flow.recordingId)).text();
const browser = await chromium.launch({headless:true, executablePath:process.env.BO_BROWSER_EXECUTABLE});
const page = await browser.newPage({viewport:{width:1520,height:1060}});
const errors = [];
page.on('pageerror', error => errors.push(String(error)));
try {
  await page.goto(base + '/graph?lang=en');
  await page.waitForFunction(() => window.graphDebug?.graph && !graphDebug.layoutBusy);
  await page.selectOption('#analysis-view', 'business');
  await page.selectOption('#record-list', flow.recordingId);
  await page.waitForSelector('#recording-timeline canvas', {state:'visible'});
  await page.selectOption('.trace-scope', 'all');
  await page.selectOption('.trace-depth', 'all');
  await page.click('.trace-maximize');
  await page.click('.trace-fit');
  await page.waitForFunction(() => !graphDebug.timeline.zooming && graphDebug.timeline.routes.length > 0);
  const allRoutes = await page.evaluate(() => graphDebug.timeline.routes.length);
  await page.selectOption('.trace-depth', 'state');
  await page.waitForFunction(() => !graphDebug.timeline.zooming && graphDebug.timeline.rows.some(row => row.layer === 'state')
    && graphDebug.timeline.rows.every(row => ['business','state'].includes(row.layer)));
  const timeline = await page.evaluate(() => graphDebug.timeline);
  assert.ok(timeline.rows.every(row => ['business','state'].includes(row.layer)));
  await page.screenshot({path:path.join(out, 'state-residency-and-calls.png')});
  await page.click('.trace-maximize');
  if (await page.locator('#layered-toggle').innerText() !== '3D') await page.click('#layered-toggle');
  await page.waitForFunction(() => !!graphDebug.spatial?.camera);
  const before = await page.evaluate(() => JSON.stringify(graphDebug.spatial.camera.position));
  const box = await page.locator('#viewport').boundingBox();
  const start = {x:box.x+box.width*.75,y:box.y+box.height*.35};
  await page.mouse.move(start.x,start.y); await page.mouse.down();
  await page.mouse.move(start.x+120,start.y+50,{steps:12}); await page.mouse.up();
  await page.waitForFunction(old => JSON.stringify(graphDebug.spatial.camera.position) !== old,before);
  await page.screenshot({path:path.join(out,'actual-orbit-and-timeline.png')});
  const after = await (await fetch(base + '/api/recordings/' + flow.recordingId)).text();
  assert.equal(after,original);
  assert.deepEqual(errors,[]);
  await writeFile(path.join(out,'visual-proof.json'),JSON.stringify({passed:true,recordingId:flow.recordingId,
    recording_sha256:createHash('sha256').update(original).digest('hex'),row_layers:[...new Set(timeline.rows.map(row=>row.layer))],
    all_layer_directed_routes:allRoutes,displayed_directed_routes:timeline.routes.length,
    real_pointer_orbit:true,recording_bytes_unchanged:true,errors},null,2));
} finally {await browser.close();}
console.log(JSON.stringify({passed:true,recordingId:flow.recordingId}));
