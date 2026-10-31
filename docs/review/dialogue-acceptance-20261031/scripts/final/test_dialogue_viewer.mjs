/** Inspect the actual independent application through the canonical viewer UI. */
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

const { chromium } = createRequire(import.meta.url)('playwright');
const base = process.argv[2];
const phase = process.argv[3] || 'v1';
const output = path.resolve('docs/review/dialogue-acceptance-20261031/application-' + phase);
await mkdir(output, { recursive: true });
const browser = await chromium.launch({headless: true, executablePath: process.env.BO_BROWSER_EXECUTABLE});
const context = await browser.newContext({viewport: {width: 1520, height: 1060}, acceptDownloads: true});
const page = await context.newPage();
const errors = [];
const checks = [];
const pending = new Map(), networkFailures = [], consoleErrors = [];
page.on('pageerror', error => errors.push(String(error.stack)));
page.on('request', request => pending.set(request, new URL(request.url()).pathname));
page.on('requestfinished', request => pending.delete(request));
page.on('requestfailed', request => {networkFailures.push({path: new URL(request.url()).pathname, error: request.failure()?.errorText}); pending.delete(request);});
page.on('console', message => {if (message.type() === 'error') consoleErrors.push(message.text());});
const api = async route => {
  const response = await fetch(base + route);
  assert.ok(response.ok, `${response.status} ${route}`);
  return response.json();
};
const ready = () => page.waitForFunction(() => window.graphDebug?.graph?.boxes && !graphDebug.layoutBusy);
const save = async () => writeFile(path.join(output, 'viewer-results.json'), JSON.stringify({
  phase, url: base + '/graph', passed: checks.every(item => item.status === 'passed') && !errors.length, checks, errors, networkFailures, consoleErrors,
}, null, 2));
async function check(name, action) {
  try {
    const result = await action();
    checks.push({name, status: 'passed', result});
  } catch (error) {
    const diagnostics = await page.evaluate(() => ({url: location.href, readyState: document.readyState,
      graphReady: !!window.graphDebug?.graph, layoutBusy: window.graphDebug?.layoutBusy,
      connection: document.querySelector('#connection')?.textContent,
      layout: document.querySelector('#layout-status')?.textContent,
      canvases: document.querySelectorAll('canvas').length})).catch(() => null);
    checks.push({name, status: 'failed', error: String(error.stack), diagnostics, pending: [...pending.values()]});
    await page.screenshot({path: path.join(output, 'failure-' + checks.length + '.png'), fullPage: true}).catch(() => {});
    // A failed case is retained. Reload only to make subsequent checks independent.
    await page.goto(base + '/graph?lang=en');
    await ready();
  }
  await save();
  const latest = checks.at(-1);
  console.log(JSON.stringify({name: latest.name, status: latest.status, error: latest.error}));
}
async function overview() {
  await page.selectOption('#analysis-view', 'overview');
  await ready();
  if (await page.locator('#layered-toggle').innerText() === '3D') await page.click('#layered-toggle');
  await page.click('#show-all');
  await ready();
}
async function selectNode(id) {
  await page.fill('#node-search', id);
  await page.locator('#node-search').press('Enter');
  await page.waitForFunction(key => graphDebug.graph.byId.has(key), id);
  await page.fill('#node-search', '');
  // Query matches include aliases and field names. Select the intended exposed
  // semantic control rather than assume the first text match owns this ID.
  await page.locator(`#semantic [data-node-id="${id}"]`).evaluate(element => element.click());
}
async function menu(action) {
  await page.locator('#viewport').focus();
  await page.keyboard.press('Shift+F10');
  await page.locator(action).click();
}
const ids = () => page.evaluate(() => [...graphDebug.graph.all.keys()].sort());
try {
  await page.goto(base + '/graph?lang=en');
  await ready();
  const initial = await api('/api/view');
  const beforeEvents = initial.events.map(event => event.id);
  await writeFile(path.join(output, 'actual-view-before.json'), JSON.stringify(initial, null, 2));
  const controls = await page.locator('button[id],select[id],input[id],textarea[id]').evaluateAll(items => items.map(item => ({
    id: item.id, tag: item.tagName, label: item.getAttribute('aria-label') || item.title || item.textContent.trim(),
    visible: !!item.getClientRects().length && getComputedStyle(item).visibility !== 'hidden', disabled: item.disabled,
  })));
  await writeFile(path.join(output, 'control-inventory.json'), JSON.stringify(controls, null, 2));
  await check('Actual build loads, graph IDs and event IDs are unique', async () => {
    assert.notEqual(initial.stage, 'design');
    assert.ok(initial.model.nodes.length);
    assert.equal(new Set(initial.model.nodes.map(node => node.id)).size, initial.model.nodes.length);
    assert.equal(new Set(initial.events.map(event => event.id)).size, initial.events.length);
    return {nodes: initial.model.nodes.length, relations: initial.model.edges.length, events: initial.events.length, binding: initial.binding_status};
  });
  await check('Source and explained labels preserve graph identity and coordinates', async () => {
    await overview();
    const before = await ids();
    const positions = await page.evaluate(() => graphDebug.graph.boxes.map(node => [node.id, node.x, node.y]));
    await page.click('#name-mode');
    assert.deepEqual(await ids(), before);
    assert.deepEqual(await page.evaluate(() => graphDebug.graph.boxes.map(node => [node.id, node.x, node.y])), positions);
    await page.click('#name-mode');
    return {ids: before.length};
  });
  await check('Every configured preset and its relations render', async () => {
    const options = await page.locator('#analysis-view option').evaluateAll(items => items.map(item => ({id: item.value, label: item.textContent})));
    const result = [];
    const required = new Set(['business','states','permission','functions','api','project','code','database','data-operations']);
    // Loading the optional index can reveal API/code presets. Visit those too,
    // rather than freeze only the options present before the first index load.
    for (let optionIndex = 0; optionIndex < options.length; optionIndex++) {
      const option = options[optionIndex];
      await page.selectOption('#analysis-view', option.id);
      if (['code','project','api'].includes(option.id)) {
        await page.waitForFunction(projection => graphDebug.view.code_structure?.loaded_nodes > 0
          && graphDebug.view.code_structure.projection === projection, option.id === 'code' ? 'all' : option.id);
      }
      await ready();
      let current = await page.evaluate(() => ({nodes: graphDebug.graph.boxes.length, relations: graphDebug.presentation.edges.length,
        kinds: [...new Set(graphDebug.graph.boxes.map(node => node.type))], code: {
          enabled: graphDebug.view.code_structure?.enabled,
          loaded: graphDebug.view.code_structure?.loaded_nodes,
          status: graphDebug.view.code_structure?.status
        }}));
      const folded = {...current};
      for (let depth = 0; required.has(option.id) && current.relations === 0 && depth < 5; depth++) {
        if (!(await page.evaluate(() => graphDebug.graph.boxes.some(box => box.kids.length && !box.open)))) break;
        await page.click('#expand'); await ready();
        current = await page.evaluate(() => ({nodes: graphDebug.graph.boxes.length, relations: graphDebug.presentation.edges.length,
          kinds: [...new Set(graphDebug.graph.boxes.map(node => node.type))], code: {
            enabled: graphDebug.view.code_structure?.enabled,
            loaded: graphDebug.view.code_structure?.loaded_nodes,
            status: graphDebug.view.code_structure?.status
          }}));
      }
      if (required.has(option.id)) {
        assert.ok(current.nodes > 0, option.id + ' has no nodes');
        assert.ok(current.relations > 0, option.id + ' has no relations');
        if (option.id === 'api') {
          assert.ok(current.kinds.includes('code-endpoint'), 'API view omitted the actual registered endpoints');
          assert.ok(await page.locator('#semantic-edges [data-relation-type="code-handles"]').count(), 'API view omitted handler links');
        }
      }
      result.push({...option, ...current, folded});
      await writeFile(path.join(output, 'preset-observations.json'), JSON.stringify(result, null, 2));
      await page.screenshot({path: path.join(output, 'view-' + option.id + '.png'), fullPage: true});
      const discovered = await page.locator('#analysis-view option').evaluateAll(items => items.map(item => ({id: item.value, label: item.textContent})));
      for (const added of discovered) if (!options.some(existing => existing.id === added.id)) options.push(added);
    }
    for (const preset of ['project', 'code', 'api']) assert.ok(result.some(item => item.id === preset), 'Required optional preset not offered after loading the actual index: ' + preset);
    return result;
  });
  await check('All elements removes explicit exclusions; expand and collapse retain identities', async () => {
    await overview();
    const before = await ids();
    const target = await page.evaluate(() => graphDebug.graph.boxes.find(box => box.type === 'business')?.id);
    assert.ok(target);
    await selectNode(target);
    await page.locator('#viewport').focus();
    await page.keyboard.press('Delete');
    assert.equal(await page.locator(`#semantic [data-node-id="${target}"]`).count(), 0);
    await page.click('#show-all');
    assert.ok(await page.locator(`#semantic [data-node-id="${target}"]`).count());
    await page.click('#expand'); await ready();
    const expanded = await page.evaluate(() => graphDebug.graph.boxes.length);
    await page.click('#collapse'); await ready();
    const collapsed = await page.evaluate(() => graphDebug.graph.boxes.length);
    assert.ok(expanded >= collapsed);
    assert.deepEqual(await ids(), before);
    return {target, expanded, collapsed};
  });
  await check('Node notes, custom label and core mark survive reload', async () => {
    await overview();
    const target = 'download';
    await selectNode(target); await menu('#annotate');
    await page.fill('#node-name', 'Download a shared file');
    await page.fill('#node-note', 'Independent trial: check current permission before downloading.');
    await page.check('#node-core');
    await page.locator('#annotation-form button[type="submit"]').click();
    await page.waitForFunction(async () => JSON.stringify(await (await fetch('/api/preferences')).json()).includes('Independent trial: check current permission'));
    await page.reload(); await ready();
    await selectNode(target);
    assert.ok((await page.locator(`#semantic [data-node-id="${target}"]`).getAttribute('aria-label')).includes('Download a shared file'));
    assert.equal(await page.locator(`#semantic [data-node-id="${target}"]`).getAttribute('data-core'), 'true');
    await writeFile(path.join(output, 'preferences-for-iteration.json'), JSON.stringify(await api('/api/preferences'), null, 2));
    return {target};
  });
  await check('A real pointer drag pins the node and survives reload', async () => {
    await overview(); await selectNode('download');
    const before = await page.evaluate(() => {
      const node = graphDebug.graph.byId.get('download'), camera = graphDebug.camera;
      const canvas = document.querySelector('#viewport canvas').getBoundingClientRect();
      return {x: node.x, y: node.y, pointer: {
        x: canvas.x + camera.pan.x + (node.x + node.w / 2) * camera.scale,
        y: canvas.y + camera.pan.y + (node.y + 31) * camera.scale,
      }};
    });
    await page.mouse.move(before.pointer.x, before.pointer.y);
    await page.mouse.down();
    await page.mouse.move(before.pointer.x + 52, before.pointer.y + 32, {steps: 12});
    await page.mouse.up(); await ready();
    const moved = await page.evaluate(() => {const node = graphDebug.graph.byId.get('download'); return {x: node.x, y: node.y};});
    assert.ok(Math.hypot(moved.x - before.x, moved.y - before.y) > 1, 'The pointer did not move the actual node');
    await page.waitForFunction(async expected => {
      const document = await (await fetch('/api/preferences')).json();
      return Object.values(document.entries).some(raw => {
        try { const value = JSON.parse(raw); return value.positions?.download?.x === expected.x && value.positions.download.y === expected.y; }
        catch { return false; }
      });
    }, moved);
    await page.reload(); await ready();
    const restored = await page.evaluate(() => {const node = graphDebug.graph.byId.get('download'); return {x: node.x, y: node.y};});
    assert.deepEqual(restored, moved);
    await writeFile(path.join(output, 'dragged-node-for-iteration.json'), JSON.stringify({id: 'download', position: moved}, null, 2));
    return {before: {x: before.x, y: before.y}, restored};
  });
  await check('Full source loads through its real binding', async () => {
    await overview();
    const target = await page.evaluate(() => graphDebug.graph.boxes.find(box => graphDebug.view.manifest.bindings[box.id] && !box.node.field)?.id);
    assert.ok(target, 'No visible source binding');
    await selectNode(target); await menu('#source');
    await page.waitForFunction(() => document.querySelector('#source-code').textContent.length > 30);
    const text = await page.locator('#source-code').innerText();
    assert.match(text, /\d+\s+.*(?:def |class |import |from )/);
    await page.screenshot({path: path.join(output, 'actual-source.png'), fullPage: true});
    await page.click('#close-detail');
    return {target, displayedCharacters: text.length, highlights: await page.locator('#source-code mark').count()};
  });
  await check('Captured transaction outcome opens context without inventing a source parameter highlight', async () => {
    await overview();
    const target = 'field:db_transaction:out:committed';
    assert.ok(await page.evaluate(id => graphDebug.graph.all.has(id), target));
    await selectNode(target); await menu('#source');
    await page.waitForFunction(id => document.querySelector('#source-code').dataset.location?.endsWith(':' + id), target);
    assert.match(await page.locator('#detail-rows').innerText(), /no matching source parameter/);
    assert.equal(await page.locator('#source-code mark').count(), 0);
    assert.ok(await page.locator('#source-code [data-source-line]').count());
    await page.screenshot({path: path.join(output, 'actual-captured-outcome-context.png'), fullPage: true});
    const text = await page.locator('#source-code').innerText();
    await page.click('#close-detail');
    return {target, displayedCharacters: text.length, fabricatedParameterHighlights: 0};
  });
  await check('Custom type/relation view saves and reloads', async () => {
    await page.selectOption('#analysis-view', 'business'); await ready();
    await page.click('#filter-toggle');
    await page.fill('#custom-view-name', 'Sharing review route');
    await page.locator('#save-view button[type="submit"]').click();
    const selected = await page.inputValue('#analysis-view');
    assert.ok(selected.startsWith('custom-'));
    const before = await page.evaluate(() => graphDebug.graph.boxes.map(box => box.id).sort());
    await page.reload(); await ready();
    assert.equal(await page.inputValue('#analysis-view'), selected);
    assert.deepEqual(await page.evaluate(() => graphDebug.graph.boxes.map(box => box.id).sort()), before);
    return {selected, nodes: before.length};
  });
  await check('3D, matching legend, layer controls, routes and planar round trip', async () => {
    await overview();
    const planar = await page.evaluate(() => graphDebug.graph.boxes.map(box => [box.id, box.x, box.y]));
    await page.click('#layered-toggle');
    await page.waitForFunction(() => graphDebug.spatial?.webgl && !graphDebug.layoutBusy);
    assert.equal(await page.locator('#legend-panel').getAttribute('data-mode'), '3D');
    for (const style of ['straight','curve','orthogonal','bus']) {
      await page.selectOption('#edge-routing', style); await ready();
      assert.equal(await page.evaluate(() => graphDebug.spatial.routing), style);
    }
    await page.locator('#layer-gap').fill('320'); await ready();
    await page.click('#top-view');
    await page.screenshot({path: path.join(output, 'actual-3d.png'), fullPage: true});
    await page.click('#layered-toggle'); await ready();
    assert.equal(await page.locator('#legend-panel').getAttribute('data-mode'), '2D');
    assert.deepEqual(await page.evaluate(() => graphDebug.graph.boxes.map(box => [box.id, box.x, box.y])), planar);
    return {renderer: 'real Three.js WebGL', roundTrip: true};
  });
  await check('Language changes through the interface and preserves node IDs', async () => {
    const before = await ids();
    await page.selectOption('#language', 'zh-CN'); await page.waitForURL(/lang=zh-CN/); await ready();
    assert.equal(await page.locator('html').getAttribute('lang'), 'zh-CN');
    assert.deepEqual(await ids(), before);
    await page.screenshot({path: path.join(output, 'actual-zh.png'), fullPage: true});
    await page.selectOption('#language', 'en'); await page.waitForURL(/lang=en/); await ready();
    return {languages: ['en','zh-CN']};
  });
  await check('Viewer, source, preferences and layout actions add no business events', async () => {
    const after = await api('/api/view');
    assert.deepEqual(after.events.map(event => event.id), beforeEvents);
    return {before: beforeEvents.length, after: after.events.length};
  });
  await writeFile(path.join(output, 'actual-view-after.json'), JSON.stringify(await api('/api/view'), null, 2));
} finally {
  await save(); await browser.close();
}
if (checks.some(check => check.status !== 'passed') || errors.length) process.exitCode = 1;
