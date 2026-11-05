/** Editing near a chapter boundary must remain stable without trapping normal scrolling. */
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { startSite } from "./site_browser_fixture.mjs";

const { chromium } = createRequire(import.meta.url)("playwright");
const output = path.resolve(process.env.BO_SCROLL_EVIDENCE || ".validation/story-scroll");
await mkdir(output, { recursive: true });
const server = await startSite();
let browser;
try {
  browser = await chromium.launch({
    headless: true,
    executablePath: process.env.BO_BROWSER_EXECUTABLE,
  });
  const page = await browser.newPage({
    viewport: { width: 1000, height: 700 },
    reducedMotion: "reduce",
  });
  // Only the surrounding content is a fixture. Chapter selection is the shipped
  // module, and focus, occlusion, pointer clicks and scrolling use the browser.
  await page.route("**/editor-fixture", (route) =>
    route.fulfill({
      contentType: "text/html",
      body: `
    <style>body{margin:0;font:16px sans-serif}header{position:fixed;top:0;height:120px;background:white;z-index:2;width:100%}
    section{height:850px;padding:140px 20px 20px;box-sizing:border-box}#first{display:flex;flex-direction:column;justify-content:flex-end}
    .view-editor{width:260px;padding-bottom:30px}input,button{padding:10px}section:nth-of-type(2){background:#f4f7f5}</style>
    <header id="navigation"><a data-chapter="0" href="#first">First</a> <a data-chapter="1" href="#second">Second</a></header>
    <section id="first"><details class="view-editor" open><summary>Edit view</summary><input id="name" aria-label="Name"><button id="save">Save</button></details></section>
    <section id="second">Next chapter</section>
    <script type="module">
      import {scrollStory} from './scroll-story.mjs';
      scrollStory({scenes:document.querySelectorAll('section'),navigation:document.querySelector('header'),interactionSelector:'.view-editor',onChange:index=>document.body.dataset.active=String(index)});
      document.querySelector('#save').onclick=()=>document.body.dataset.saved='true';
    </script>`,
    }),
  );
  await page.goto(server.url + "/editor-fixture");
  await page.fill("#name", "Selected path");
  await page.evaluate(() => {
    const input = document.querySelector("#name").getBoundingClientRect();
    scrollBy({ top: input.top - 150, behavior: "instant" });
  });
  await page.waitForFunction(
    () => document.querySelector("#second").getBoundingClientRect().top < innerHeight * 0.48,
  );
  assert.equal(
    await page.getAttribute("body", "data-active"),
    "0",
    "The visible editor owns its interaction",
  );
  await page.click("#save");
  assert.equal(await page.getAttribute("body", "data-saved"), "true");
  await page.screenshot({ path: path.join(output, "editing-boundary.png") });
  await page.mouse.move(700, 500);
  await page.mouse.wheel(0, 450);
  await page.waitForFunction(() => document.body.dataset.active === "1");
  await page.locator('[data-chapter="0"]').click();
  await page.waitForFunction(() => document.body.dataset.active === "0");
  await page.fill("#name", "Second path");
  await page.locator('[data-chapter="1"]').click();
  await page.waitForFunction(() => document.body.dataset.active === "1");
  await writeFile(
    path.join(output, "result.json"),
    JSON.stringify(
      {
        passed: true,
        visible_editor: true,
        save: true,
        scroll_release: true,
        explicit_navigation: true,
      },
      null,
      2,
    ),
  );
  console.log(
    "PASS: visible editor stays in its chapter; ordinary scrolling and navigation release it.",
  );
} finally {
  await browser?.close();
  server.close();
}
