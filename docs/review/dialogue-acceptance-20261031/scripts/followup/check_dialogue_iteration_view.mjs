/** Compare the actual saved personal view before and after ordinary coding. */
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {mkdir, readFile, writeFile} from 'node:fs/promises';
import path from 'node:path';
import {gunzipSync} from 'node:zlib';

const {chromium} = createRequire(import.meta.url)('playwright');
const base = process.argv[2], phase = process.argv[3];
const before = JSON.parse(await readFile('docs/review/dialogue-acceptance-20261031/iteration/original-v1-ready-02/saved-view.json', 'utf8'));
const original = JSON.parse(await readFile('docs/review/dialogue-acceptance-20261031/iteration/original-v1-ready/snapshot.json', 'utf8'));
const oldRecords = JSON.parse(gunzipSync(await readFile('docs/review/dialogue-acceptance-20261031/iteration/original-v1-ready/recordings.json.gz')).toString('utf8'));
const out = path.resolve('docs/review/dialogue-acceptance-20261031/iteration', phase);
await mkdir(out, {recursive: true});
const browser = await chromium.launch({headless: true, executablePath: process.env.BO_BROWSER_EXECUTABLE});
const page = await browser.newPage({viewport: {width: 1520, height: 1060}});
const result = {base, phase, checks: [], errors: []};
page.on('pageerror', error => result.errors.push(String(error.stack)));
const api = async route => {const response = await fetch(base + route); assert.ok(response.ok); return response.json();};
try {
  const view = await api('/api/view'), prefs = await api('/api/preferences'), records = await api('/api/recordings');
  assert.equal(view.binding_status.status, 'current');
  assert.notEqual(view.manifest.build_id, original.build_id);
  const current = JSON.parse(prefs.entries[before.viewState.key]);
  for (const key of ['nodes', 'edges', 'regions', 'hiddenNodes', 'hiddenEdges', 'depth'])
    assert.deepEqual(current.filters[key], before.viewState.value.filters[key], 'Saved filter changed: ' + key);
  assert.deepEqual(current.positions.download, before.viewState.value.positions.download);
  assert.deepEqual(current.annotations.download, before.viewState.value.annotations.download);
  assert.ok(current.expanded.includes('share'));
  result.checks.push({name: 'Saved type/individual filters, dragged pin, expansion and annotation survive source update'});
  const oldMembers = before.hiddenRelation.members;
  for (const relation of oldMembers) {
    const found = view.model.edges.find(edge => edge.id === relation.id);
    assert.ok(found, 'An unchanged relation lost its stable identity: ' + relation.id);
    assert.equal(found.from, relation.from); assert.equal(found.to, relation.to); assert.equal(found.type, relation.type);
  }
  result.checks.push({name: 'The hidden relation still identifies the same actual endpoints', ids: oldMembers.map(edge => edge.id)});
  assert.equal(records.active, null);
  const obsoleteIds = new Set(oldRecords.recordings.map(record => record.id));
  assert.ok(records.recordings.every(record => !obsoleteIds.has(record.id)), 'Obsolete current-list recordings survived a changed graph build');
  for (const item of records.recordings) {
    const recording = await api('/api/recordings/' + item.id);
    assert.equal(recording.context.manifest.build_id, view.manifest.build_id);
  }
  result.checks.push({name: 'The new graph build removes old recordings and keeps only current-build records', old: [...obsoleteIds], current: records.recordings.map(record => record.id)});
  const initialEventIds = view.events.map(event => event.id);
  const analysisKey = before.viewState.key.split(':view:')[0] + ':analysis';
  result.selectionBeforeNavigation = JSON.parse(prefs.entries[analysisKey]).selected;
  await page.goto(base + '/graph?lang=en');
  await page.waitForFunction(() => window.graphDebug?.graph && !graphDebug.layoutBusy);
  assert.equal(await page.inputValue('#analysis-view'), result.selectionBeforeNavigation);
  // The confirmed design-preview browser intentionally focused its new scope in
  // overview between the baseline and coding. Test the retained personal view by
  // choosing it normally; do not mistake that prior UI action for source drift.
  if (result.selectionBeforeNavigation !== before.selectedView) {
    result.interveningSelection = {selected: result.selectionBeforeNavigation, evidence: 'design-review-supplement/supplemental-flow-draft.png', savedViewRetained: before.selectedView};
    await page.selectOption('#analysis-view', before.selectedView);
    await page.waitForFunction(() => !graphDebug.layoutBusy);
    await page.waitForFunction(async expected => {
      const preferences = await (await fetch('/api/preferences')).json();
      return JSON.parse(preferences.entries[expected.key]).selected === expected.id;
    }, {key: analysisKey, id: before.selectedView});
  }
  await page.reload();
  await page.waitForFunction(() => window.graphDebug?.graph && !graphDebug.layoutBusy);
  assert.equal(await page.inputValue('#analysis-view'), before.selectedView);
  assert.equal(await page.locator('#semantic [data-node-id="logout"]').count(), 0);
  assert.equal(await page.locator('#semantic [data-node-id="share"]').getAttribute('aria-expanded'), 'true');
  const restored = await page.evaluate(() => {const node=graphDebug.graph.byId.get('download'); return {id:node.id,x:node.x,y:node.y};});
  assert.deepEqual(restored, before.pinnedNode);
  assert.ok((await page.locator('#semantic [data-node-id="download"]').getAttribute('aria-label')).includes('Download a shared file'));
  assert.equal(await page.locator('#semantic [data-node-id="download"]').getAttribute('data-core'), 'true');
  assert.equal(await page.locator(`#semantic-edges [data-edge-id="${before.hiddenRelation.id}"]`).count(), 0);
  result.checks.push({name: 'Choosing the retained view restores hidden/expanded state and survives a fresh native reload'});
  await page.screenshot({path: path.join(out, 'saved-view-after-iteration.png')});
  const after = await api('/api/view');
  assert.deepEqual(after.events.map(event => event.id), initialEventIds, 'Restoring the view generated business observations');
  result.checks.push({name: 'Restoring personal view settings emits zero application events'});
  result.passed = !result.errors.length;
  result.buildId = view.manifest.build_id;
} catch (error) {
  result.passed = false; result.error = String(error.stack);
  await page.screenshot({path: path.join(out, 'saved-view-update-failure.png')}).catch(() => {});
} finally {
  await writeFile(path.join(out, 'view-update.json'), JSON.stringify(result, null, 2));
  await browser.close();
}
console.log(JSON.stringify({passed: result.passed, checks: result.checks.length, error: result.error}));
if (!result.passed) process.exitCode = 1;
