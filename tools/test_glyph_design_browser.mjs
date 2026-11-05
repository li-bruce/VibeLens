/** Inspect the actual 2D legend and rendered 3D objects, then real replay arrows. */
import assert from "node:assert/strict";
import {createRequire} from "node:module";
import {mkdir, writeFile} from "node:fs/promises";
import path from "node:path";
import {serveRecording} from "./recording_browser_fixture.mjs";
import {timeline} from "../skills/vibelens/assets/stategraph-viewer/recording.js";
const {chromium} = createRequire(import.meta.url)("playwright");
const output = path.resolve(process.env.BO_GLYPH_EVIDENCE || ".validation/glyph-design");
await mkdir(output, {recursive: true});
const recordingPath = "docs/review/spatial-workspace/replay-fixture.json";
const fixture = await serveRecording(recordingPath);
const browser = await chromium.launch({headless: true,
  executablePath: process.env.BO_BROWSER_EXECUTABLE, args: ["--enable-unsafe-swiftshader"]});
const page = await browser.newPage({viewport: {width: 1440, height: 1000}, deviceScaleFactor: 2});
const errors = [];
page.on("pageerror", error => errors.push(String(error)));
try {
  await page.goto(fixture.url + "?lang=en");
  await page.waitForFunction(() => window.graphDebug?.graph && !graphDebug.layoutBusy);
  const gallery = await page.evaluate(async () => {
    const {legendGlyph} = await import("/glyphs.js");
    const {spatialLegend} = await import("/spatial-geometry.js");
    const {layerPalette} = await import("/layer-style.js");
    const entries = [
      ["business", "business", "Business flow"], ["state", "state", "State"],
      ["decision", "rules", "Rule"], ["code-endpoint", "entry", "Entry point"],
      ["code-directory", "structure", "Directory"], ["code-file", "structure", "Source file"],
      ["code-function", "symbols", "Function"], ["resource", "rules", "Resource"],
      ["store", "data", "Storage"],
    ];
    const styles = Object.fromEntries(entries.map(([type, layer]) => [type, {color: layerPalette[layer]}]));
    const solids = spatialLegend(styles);
    const section = document.createElement("section"); section.id = "glyph-review";
    Object.assign(section.style, {position:"fixed", inset:0, zIndex:1000, background:"#f7f9f8",
      padding:"40px 80px", fontFamily:"Segoe UI, sans-serif", color:"#173b36", overflow:"auto"});
    section.innerHTML = '<h1 style="font-size:30px;font-weight:500;margin:0">VibeLens · One visual language</h1><p style="color:#667b75;margin:10px 0 28px">2D icons &nbsp; / &nbsp; 3D objects</p><div id="glyph-grid" style="display:grid;grid-template-columns:repeat(3,1fr);gap:22px 44px"></div>';
    for (const [type, layer, label] of entries) {
      const card = document.createElement("div");
      card.style = "border-top:1px solid #d7e2dc;padding:18px 8px";
      const title = document.createElement("h2");title.textContent = label;
      title.style = "font-size:16px;font-weight:500;margin:0";
      const row = document.createElement("div"); row.style = "display:flex;align-items:center;gap:46px;height:160px";
      const glyph = legendGlyph(type, styles[type]); glyph.style = "width:66px;height:66px";
      const image = document.createElement("img"); image.src = solids.get(type);
      image.alt = label; image.style = "width:140px;height:140px;object-fit:contain";
      row.append(glyph, image);card.append(title, row); section.querySelector("#glyph-grid").append(card);
    }
    document.body.append(section);
    await Promise.all([...section.querySelectorAll("img")].map(image => image.decode()));
    return entries.map(([type, layer]) => ({type, layer, color: styles[type].color}));
  });
  await page.screenshot({path:path.join(output,"node-vocabulary.png")});
  await page.locator("#glyph-review").evaluate(element => element.remove());
  await page.selectOption("#record-list", fixture.recording.id);
  await page.selectOption("#replay-grain", "events");
  // A committed transition has recorded input/output evidence. Use its native
  // state view rather than expecting transfers through collapsed hidden nodes.
  await page.selectOption("#analysis-view", "states");
  const committed = fixture.recording.runtime_frames.frames[1].event_id;
  const event = String(timeline(fixture.recording).findIndex(item => item.id === committed));
  assert.notEqual(event, "-1", "The committed transition belongs to the real recording");
  const transfers = {};
  for (const mode of ["2D", "3D"]) {
    if (await page.locator("#layered-toggle").innerText() !== mode) await page.click("#layered-toggle");
    await page.waitForFunction(() => !graphDebug.layoutBusy);
    await page.selectOption("#replay-events", event);
    await page.waitForFunction(() => document.querySelector("#renderer").dataset.animationActive === "true"
      && JSON.parse(document.querySelector("#renderer").dataset.animatedEdges || "[]").length > 0);
    transfers[mode] = await page.locator("#renderer").evaluate(element => JSON.parse(element.dataset.animatedEdges));
    await page.screenshot({path:path.join(output, `transfer-${mode}.png`)});
  }
  assert.deepEqual(transfers["2D"], transfers["3D"], "Both renderers animate the same recorded edges");
  assert.deepEqual(errors, []);
  assert.equal(fixture.writes.length, 0);
  await writeFile(path.join(output,"result.json"), JSON.stringify({valid:true,gallery,recordingPath,event,transfers,errors, businessWrites:0},null,2));
  console.log("PASS: matched 2D/3D vocabulary and real recording transfers in both renderers.");
} catch (error) {
  await writeFile(path.join(output,"failure.json"), JSON.stringify({valid:false,error:String(error),errors},null,2));
  throw error;
} finally {await browser.close(); await fixture.close();}
