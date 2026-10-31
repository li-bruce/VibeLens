/** Real focused capture and restored full capture use the application's native probes. */
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {mkdir, writeFile} from 'node:fs/promises';
import path from 'node:path';
const {chromium} = createRequire(import.meta.url)('playwright');
const application = process.argv[2], observer = process.argv[3];
const out = path.resolve('docs/review/dialogue-acceptance-20261031/' + (process.argv[4] || 'focused-actual'));
await mkdir(out, {recursive:true});
const browser = await chromium.launch({headless:true, executablePath:process.env.BO_BROWSER_EXECUTABLE});
const owner = await browser.newPage(), reviewer = await browser.newPage();
const viewer = await browser.newPage({viewport:{width:1520,height:1060}});
const checks = [], errors = [], result = {application,observer,checks,errors};
for (const page of [owner,reviewer,viewer]) page.on('pageerror', error => errors.push(String(error.stack)));
const api = async route => {const response = await fetch(observer + route); assert.ok(response.ok); return response.json();};
async function login(page, name) {
  await page.goto(application + '/');
  await page.fill('input[name="username"]',name);
  await page.fill('input[name="password"]','TrialOnly!2026');
  await page.locator('form').filter({has:page.locator('input[name="username"]')}).locator('button').click();
  await page.waitForSelector('#my-files');
}
async function stop() {
  const request = viewer.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith('/api/recordings/stop'), {timeout:45000});
  await viewer.click('#record-stop');
  const response = await request;
  assert.ok(response.ok()); await response.finished();
  await viewer.waitForFunction(() => document.querySelector('#record-stop').disabled);
}
async function start(mode) {
  await viewer.selectOption('#capture-mode',mode);
  const request = viewer.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith('/api/recordings/start'), {timeout:45000});
  await viewer.click('#record-start');
  const response = await request;
  assert.ok(response.ok()); await response.finished();
  const state = await api('/api/recordings');
  return typeof state.active === 'string' ? state.active : state.active.id;
}
try {
  await login(owner,'owner'); await login(reviewer,'reviewer');
  const name = 'focused-' + Date.now() + '.txt';
  await owner.setInputFiles('input[type="file"]',{name,mimeType:'text/plain',buffer:Buffer.from('Actual focused capture trial\n')});
  await owner.locator('form').filter({has:owner.locator('input[name="action"][value="upload"]')}).locator('button').click();
  const row = owner.locator('#my-files .file-row').filter({hasText:name});
  await row.locator('summary').click();
  const file = await row.locator('input[name="file_id"]').inputValue();
  await row.locator('select[name="recipient_id"]').selectOption('recipient');
  await row.locator('select[name="reviewer_id"]').selectOption('reviewer');
  await row.locator('.share-form button').click();
  const share = await owner.locator('.history-row').filter({hasText:name}).locator('input[name="share_id"]').inputValue();
  await reviewer.goto(application + '/');
  await viewer.goto(observer + '/graph?lang=en');
  await viewer.waitForFunction(() => window.graphDebug?.graph && !graphDebug.layoutBusy);
  // A copied personal state-only view intentionally omits business actions.
  // Select the relevant native perspective before selecting the exact action.
  await viewer.selectOption('#analysis-view','business');
  await viewer.click('#show-all');
  await viewer.waitForSelector('#semantic [data-node-id="review"]',{state:'attached'});
  await viewer.locator('#semantic [data-node-id="review"]').evaluate(element => element.click());
  await viewer.fill('#node-search','');
  const id = await start('focused');
  const started = await api('/api/recordings/' + id);
  assert.ok(started.capture.nodes.includes('review'));
  const action = reviewer.locator('#reviews form').filter({has:reviewer.locator(`input[name="share_id"][value="${share}"]`)}).filter({has:reviewer.locator('button[value="approve"]')});
  await action.locator('button').click();
  await stop();
  const focused = await api('/api/recordings/' + id);
  await writeFile(path.join(out,'focused-recording.json'),JSON.stringify(focused,null,2));
  assert.equal(focused.status,'stopped',focused.gaps.join('; '));
  assert.deepEqual(focused.gaps,[]);
  assert.ok(focused.events.length);
  assert.ok(focused.events.every(event => focused.capture.nodes.includes(event.node)));
  assert.ok(focused.events.some(event => event.node === 'review' && event.phase === 'return' && event.outputs.state === 'approved'));
  assert.equal(focused.final.machine.current,'approved');
  assert.ok(focused.final.health.producer.filtered > focused.context.health.producer.filtered);
  assert.equal(focused.final.health.producer.data_errors,0);
  await viewer.screenshot({path:path.join(out,'focused-approval.png')});
  checks.push({name:'Real focused approval keeps its state frame and captured scope',events:focused.events.length,capture:focused.capture});
  await viewer.click('#replay-live');
  await viewer.waitForFunction(() => !graphDebug.view.replay);
  const fullId = await start('all');
  const response = await owner.request.get(application + '/download/' + file);
  assert.equal(response.status(),200);
  assert.equal((await response.body()).toString('utf8'),'Actual focused capture trial\n');
  await stop();
  const full = await api('/api/recordings/' + fullId);
  await writeFile(path.join(out,'restored-full-recording.json'),JSON.stringify(full,null,2));
  assert.equal(full.status,'stopped',full.gaps.join('; '));
  assert.ok(full.events.some(event => event.node === 'db_read'));
  assert.ok(full.events.some(event => event.node === 'http_download'));
  assert.deepEqual(full.gaps,[]);
  assert.equal(full.capture.nodes,null);
  checks.push({name:'Stopping focused capture restores actual HTTP and data capture',events:full.events.length});
  assert.deepEqual(errors,[]);
  result.passed = true;
} catch(error) {
  result.passed = false; result.error=String(error.stack);
  await viewer.screenshot({path:path.join(out,'failure.png')}).catch(()=>{});
  console.error(result.error);
} finally {
  await writeFile(path.join(out,'results.json'),JSON.stringify(result,null,2));
  await browser.close();
}
console.log(JSON.stringify({passed:result.passed,checks:checks.length,error:result.error}));
if(!result.passed)process.exitCode=1;
