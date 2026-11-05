/** Synthetic presentation load: real Canvas/pointers, no claim of business execution. */
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { serveRecording } from "./recording_browser_fixture.mjs";

const { chromium } = createRequire(import.meta.url)("playwright");
const out = path.resolve(process.env.BO_TIMELINE_EVIDENCE || ".validation/timeline-performance");
await mkdir(out, { recursive: true });
const fixture = await serveRecording(
  path.resolve("docs/review/spatial-workspace/replay-fixture.json"),
);
const html = `<!doctype html><html><head><link rel="stylesheet" href="/viewer.css"><link rel="stylesheet" href="/timeline.css"></head>
<body><div style="flex:1;padding:20px">Synthetic timeline load · 20,000 events</div><section id="recording-timeline"></section>
<script type="module">
import { RecordingTimeline } from '/recording-timeline.js';
import { timeline } from '/recording.js';
const nodes = [
 {id:'business',label:'Share file',kind:'action',layer:'business'},
 {id:'state',label:'Shared',kind:'state',value:'shared'},
 {id:'rules',label:'Check access',kind:'decision'},
 {id:'api',label:'POST /files/share',kind:'function',code_role:'endpoint'},
 {id:'function',label:'share_file',kind:'function'},
 {id:'query',label:'Read grants',kind:'function',data_role:'query'},
 {id:'file',label:'access.py',kind:'function',code_role:'file'},
 {id:'symbol',label:'Access.can_share',kind:'function',code_role:'function'},
 {id:'data',label:'grants',kind:'data',data_role:'dataset'}];
const at = ms => new Date(Date.UTC(2026,9,30) + ms).toISOString();
const events = Array.from({length:20000},(_,i)=>({id:'event:'+i,seq:i+1,phase:i%2?'return':'enter',
node:nodes[Math.floor(i/2)%nodes.length].id,call_id:'call:'+Math.floor(i/2),run_id:'run',producer_id:'worker',
build_id:'build',entity:'file:'+Math.floor(i/100),attempt:'attempt',inputs:{},outputs:{value:i},depends:i>1 && i%2===0 ? [{event:"event:"+(i-1),type:"control"}] : [],observed_at:at(i+1)}));
const recording = {id:'load',status:'stopped',started_at:at(0),ended_at:at(20001),events,commands:[],gaps:[],
context:{model:{nodes,edges:[],machine:{}},events:[],machine:{configurations:[]}},final:{machine:{configurations:[]}}};
const items=timeline(recording), all=new Map(nodes.map(node=>[node.id,node]));
let raw=0, settings={visible:true,height:380,scope:'all',expanded:[],follow:true};
const seeks=[], paints=[];
const input=()=>({recording,items,all,edges:[],visible:new Set(all.keys()),plan:items.map((_,i)=>i),raw,transfers:[],settings,playing:false,selection:{loop:false}});
const component=new RecordingTimeline(document.getElementById('recording-timeline'),{
 onSeek(index){const start=performance.now();raw=index;component.update(input());requestAnimationFrame(()=>{seeks.push(performance.now()-start);paints.push(component.diagnostics.paintMs);});},
 onPause(){},onRange(){},onSettings(value){settings=value;component.update(input());}
});
const start=performance.now();component.update(input());
requestAnimationFrame(()=>{window.tracePerf={ready:true,indexAndFirstPaintMs:performance.now()-start,
 get state(){return component.diagnostics;},get seeks(){return [...seeks];},get paints(){return [...paints];}};});
window.addEventListener('pagehide',()=>component.dispose());
</script></body></html>`;
let browser, page;
const errors = [];
let measured = null;
try {
  browser = await chromium.launch({
    headless: true,
    executablePath: process.env.BO_BROWSER_EXECUTABLE,
  });
  page = await browser.newPage({ viewport: { width: 1440, height: 960 } });
  page.on("pageerror", (error) => errors.push(String(error.stack)));
  await page.route("**/timeline-benchmark", (route) =>
    route.fulfill({ contentType: "text/html", body: html }),
  );
  await page.goto(fixture.url.replace("/graph", "/timeline-benchmark"));
  await page.waitForFunction(() => window.tracePerf?.ready);
  const canvas = page.locator("#recording-timeline canvas"),
    box = await canvas.boundingBox();
  let state = await page.evaluate(() => tracePerf.state);
  await page.mouse.move(box.x + state.geometry.left + 10, box.y + 38);
  await page.mouse.down();
  for (let i = 1; i <= 40; i++) {
    await page.mouse.move(box.x + state.geometry.left + (state.geometry.plot * i) / 42, box.y + 38);
    await page.waitForTimeout(20); // Simulate a sustained drag rather than one coalesced input burst.
  }
  await page.mouse.up();
  await page.waitForTimeout(80);
  await page.mouse.move(box.x + state.geometry.left + state.geometry.plot * 0.6, box.y + 38);
  await page.keyboard.down("Control");
  await page.mouse.wheel(0, -500);
  await page.keyboard.up("Control");
  await page.waitForTimeout(80);
  // Collapse/expand an execution band without adding per-node tracks.
  await page.mouse.click(box.x + 50, box.y + state.geometry.top + 14);
  assert.equal((await page.evaluate(() => tracePerf.state)).rows.length, 1);
  await page.mouse.click(box.x + 50, box.y + state.geometry.top + 14);
  await page.waitForTimeout(50);
  await page.screenshot({ path: path.join(out, "timeline-20000-events.png") });
  const perf = await page.evaluate(() => ({
    initialMs: tracePerf.indexAndFirstPaintMs,
    seeks: tracePerf.seeks,
    paints: tracePerf.paints,
    state: tracePerf.state,
  }));
  const percentile = (values, p) =>
    [...values].sort((a, b) => a - b)[Math.min(values.length - 1, Math.floor(values.length * p))];
  const report = {
    passed: true,
    browser: browser.version(),
    platform: process.platform,
    viewport: { width: 1440, height: 960 },
    kind: "synthetic Canvas component load; excludes graph reconstruction",
    eventCount: 20000,
    causalLinks: 9999,
    drawnFlows: perf.state.flows,
    initialMs: perf.initialMs,
    seekCount: perf.seeks.length,
    seekP95Ms: percentile(perf.seeks, 0.95),
    drawP95Ms: percentile(perf.paints, 0.95),
    paintedPrimitives: perf.state.painted,
    visibleRows: perf.state.rows.length,
    semanticLayers: new Set(perf.state.rows.map((row) => row.layer)).size,
    errors,
  };
  measured = report;
  assert.ok(perf.seeks.length >= 20, "pointer drag produces many real seeks");
  assert.equal(
    report.semanticLayers,
    7,
    "all seven display planes participate in the load fixture",
  );
  assert.equal(
    report.visibleRows,
    7,
    "20k sequential events reuse seven plane rows across nine node roles",
  );
  assert.deepEqual(
    [...new Set(perf.state.rows.map((row) => row.layer))].sort(),
    ["business", "state", "rules", "entry", "structure", "symbols", "data"].sort(),
  );
  assert.ok(report.initialMs < 2500);
  assert.ok(report.seekP95Ms < 100, "20k timeline seek/render p95 under 100 ms on this host");
  assert.ok(report.drawP95Ms < 60);
  assert.ok(
    report.drawnFlows > 0 && report.drawnFlows <= 1804,
    "window/pixel culling bounds causal chain drawing",
  );
  assert.ok(perf.state.painted < 6000, "pixel aggregation bounds drawing");
  assert.deepEqual(errors, []);
  await writeFile(path.join(out, "result.json"), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
} catch (error) {
  await page?.screenshot({ path: path.join(out, "failure.png") }).catch(() => {});
  await writeFile(
    path.join(out, "result.json"),
    JSON.stringify({ ...measured, passed: false, errors, error: String(error.stack) }, null, 2),
  );
  throw error;
} finally {
  await browser?.close();
  await fixture.close();
}
