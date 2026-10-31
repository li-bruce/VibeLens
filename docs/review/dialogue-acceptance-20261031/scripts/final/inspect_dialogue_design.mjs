import { createRequire } from 'node:module';
import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
const { chromium } = createRequire(import.meta.url)('playwright');
const base = process.argv[2];
const out = path.resolve(process.argv[3] || 'docs/review/dialogue-acceptance-20261031/design');
await mkdir(out, { recursive: true });
const browser = await chromium.launch({headless: true, executablePath: process.env.BO_BROWSER_EXECUTABLE});
const page = await browser.newPage({viewport: {width: 1520, height: 1060}});
const errors = [];
page.on('pageerror', error => errors.push(String(error.stack)));
try {
  await page.goto(base + '/graph?lang=zh-CN');
  await page.waitForFunction(() => window.graphDebug?.graph?.boxes.length > 0 && !graphDebug.layoutBusy);
  const state = await page.evaluate(async () => ({
    design: await (await fetch('/api/design')).json(),
    view: await (await fetch('/api/view')).json(),
    nodes: [...graphDebug.graph.all.values()],
    edges: graphDebug.graph.rawEdges,
  }));
  await page.screenshot({path: path.join(out, process.argv[4] || 'confirmed-intent-draft.png'), fullPage: true});
  await writeFile(path.join(out, 'actual-design.json'), JSON.stringify(state, null, 2));
  assert.equal(state.view.stage, 'design');
  assert.ok(state.nodes.length > 0 && state.edges.length > 0);
  assert.equal(state.view.events?.length || 0, 0);
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({url: base + '/graph', stage: state.view.stage, nodes: state.nodes.length, edges: state.edges.length, eventCount: state.view.events?.length, errors}));
} finally { await browser.close(); }
