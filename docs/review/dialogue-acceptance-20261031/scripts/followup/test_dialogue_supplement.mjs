/** Exercise the ordinary iteration through real forms and read-only database facts. */
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {spawnSync} from 'node:child_process';
import {mkdir, writeFile} from 'node:fs/promises';
import path from 'node:path';

const {chromium} = createRequire(import.meta.url)('playwright');
const application = process.argv[2], observer = process.argv[3], phase = process.argv[4];
const out = path.resolve('docs/review/dialogue-acceptance-20261031/operations-' + phase);
await mkdir(out, {recursive: true});
const trial = path.resolve(process.env.BO_DIALOGUE_TRIAL_ROOT || '../VibeLensTrials/lifecycle-dialogue-20261031');
const python = path.resolve('.venv/Scripts/python.exe');
const browser = await chromium.launch({headless: true, executablePath: process.env.BO_BROWSER_EXECUTABLE});
const viewer = await browser.newPage({viewport: {width: 1520, height: 1060}});
const contexts = {}, pages = {}, checks = [], errors = [];
const result = {application, observer, phase, checks, errors};
const api = async route => {
  const response = await fetch(observer + route);
  assert.ok(response.ok, route + ': ' + response.status);
  return response.json();
};
const shot = (page, name) => page.screenshot({path: path.join(out, name + '.png'), fullPage: true});

// Native facts come from a fresh read-only connection, independent of graph output.
function facts(share) {
  const source = `import json,sqlite3,sys
from pathlib import Path
with sqlite3.connect(Path(sys.argv[1]).as_uri()+"?mode=ro",uri=True) as db:
 db.row_factory=sqlite3.Row
 print(json.dumps({"share":dict(db.execute("SELECT * FROM shares WHERE id=?",(sys.argv[2],)).fetchone()),"notifications":[dict(r) for r in db.execute("SELECT * FROM notifications WHERE share_id=? ORDER BY id",(sys.argv[2],))],"journal":[dict(r) for r in db.execute("SELECT * FROM journal WHERE share_id=? ORDER BY revision",(sys.argv[2],))]}))`;
  const response = spawnSync(python, ['-B', '-X', 'utf8', '-c', source, path.join(trial, 'data/application.sqlite3'), share], {encoding: 'utf8', windowsHide: true});
  assert.equal(response.status, 0, response.stderr);
  return JSON.parse(response.stdout);
}
async function login(user) {
  const context = contexts[user] = await browser.newContext({acceptDownloads: true, viewport: {width: 1280, height: 950}});
  const page = pages[user] = await context.newPage();
  page.on('pageerror', error => errors.push(user + ': ' + String(error)));
  await page.goto(application + '/');
  await page.fill('input[name="username"]', user);
  await page.fill('input[name="password"]', 'TrialOnly!2026');
  await page.locator('form').filter({has: page.locator('input[name="username"]')}).locator('button').first().click();
  await page.waitForSelector('#my-files');
}
async function setup(name) {
  const owner = pages.owner;
  await owner.goto(application + '/');
  const content = 'Independent ordinary iteration / ' + name + '\n';
  await owner.setInputFiles('input[type="file"]', {name, mimeType: 'text/plain', buffer: Buffer.from(content)});
  await owner.locator('form').filter({has: owner.locator('input[name="action"][value="upload"]')}).locator('button').click();
  const row = owner.locator('#my-files .file-row').filter({hasText: name});
  await row.locator('summary').click();
  await row.locator('select[name="recipient_id"]').selectOption('recipient');
  await row.locator('select[name="reviewer_id"]').selectOption('reviewer');
  const file = await row.locator('input[name="file_id"]').inputValue();
  await row.locator('.share-form button').click();
  const history = owner.locator('.history-row').filter({hasText: name});
  const share = await history.locator('input[name="share_id"]').inputValue();
  assert.equal(facts(share).share.state, 'pending');
  return {filename: name, file, share, content, download: application + '/download/' + file};
}
async function open(user, record) {
  const response = await pages[user].goto(application + '/application/' + record.share);
  assert.equal(response.status(), 200);
  return pages[user];
}
async function nativeAction(user, record, action, field, text) {
  const page = await open(user, record);
  if (field) await page.fill('[name="' + field + '"]', text);
  await page.locator('button[name="action"][value="' + action + '"]').click();
  await page.waitForSelector('#my-files');
}
async function denied(user, record, action, extra = {}) {
  const before = facts(record.share);
  const csrf = await pages[user].locator('input[name="csrf"]').first().inputValue();
  const response = await contexts[user].request.post(application + '/', {form: {csrf, action, share_id: record.share, ...extra}, maxRedirects: 0});
  assert.equal(response.status(), 303);
  assert.deepEqual(facts(record.share), before, user + '/' + action + ' changed native records');
}
async function privateDenied(user, record, secretTexts) {
  const response = await contexts[user].request.get(application + '/application/' + record.share);
  assert.equal(response.status(), 403);
  const content = await response.text();
  for (const text of secretTexts) assert.equal(content.includes(text), false);
}

let started = false;
try {
  viewer.on('pageerror', error => errors.push('graph: ' + String(error)));
  for (const user of ['owner', 'recipient', 'reviewer']) await login(user);
  const stamp = Date.now();
  const main = result.approved = await setup('supplement-rounds-' + stamp + '.txt');
  const cancel = result.cancelled = await setup('supplement-cancel-' + stamp + '.txt');
  const reject = result.rejected = await setup('supplement-reject-' + stamp + '.txt');
  await viewer.goto(observer + '/graph?lang=en');
  await viewer.waitForFunction(() => window.graphDebug?.graph && !graphDebug.layoutBusy);
  await viewer.selectOption('#analysis-view', 'business');
  await viewer.selectOption('#capture-mode', 'all');
  await viewer.click('#record-start');
  await viewer.waitForFunction(() => !document.querySelector('#record-stop').disabled);
  const start = await api('/api/recordings');
  result.recordingId = typeof start.active === 'string' ? start.active : start.active.id;
  started = true;
  // An actual fourth login also supplies a short measured call for zoom inspection.
  await login('other');
  checks.push({name: 'Four isolated real browser users and three ordinary pending shares'});

  const reasonOne = 'Usage rights need clarification / ' + stamp;
  const noteOne = 'Owner confirms the image license / ' + stamp;
  const reasonTwo = 'Please identify the allowed audience / ' + stamp;
  const noteTwo = 'Access is limited to the selected member / ' + stamp;
  await denied('other', main, 'return_share', {reason: reasonOne});
  await denied('reviewer', main, 'return_share', {reason: ' '});
  await denied('reviewer', main, 'return_share', {reason: 'x'.repeat(201)});
  await denied('owner', main, 'resubmit_share', {explanation: noteOne});
  checks.push({name: 'Wrong reviewer, blank/201-character reason and premature resubmission preserve native state/messages/history'});

  await nativeAction('reviewer', main, 'return_share', 'reason', reasonOne);
  let actual = facts(main.share);
  assert.equal(actual.share.state, 'awaiting_supplement');
  assert.equal(actual.share.return_reason, reasonOne);
  assert.equal(actual.share.supplement_text, '');
  assert.deepEqual(actual.notifications.map(item => [item.user_id, item.kind]), [['owner', 'returned']]);
  const owner = await open('owner', main);
  assert.ok((await owner.locator('.application-panel').innerText()).includes(reasonOne));
  await shot(owner, 'owner-awaiting-supplement');
  await denied('reviewer', main, 'approve');
  await denied('reviewer', main, 'reject');
  await denied('other', main, 'resubmit_share', {explanation: noteOne});
  await denied('owner', main, 'resubmit_share', {explanation: ' '});
  await denied('owner', main, 'resubmit_share', {explanation: 'x'.repeat(201)});
  await privateDenied('recipient', main, [reasonOne]);
  await privateDenied('other', main, [reasonOne]);
  assert.equal((await contexts.recipient.request.get(main.download)).status(), 403);
  await pages.recipient.goto(application + '/');
  assert.equal(await pages.recipient.locator('#received').getByText(main.filename, {exact: true}).count(), 0);
  assert.equal(await pages.recipient.locator('#messages .message').filter({hasText: main.filename}).count(), 0);
  checks.push({name: 'Awaiting supplement blocks review/download, limits the notice to owner and keeps text private'});

  await nativeAction('owner', main, 'resubmit_share', 'explanation', noteOne);
  actual = facts(main.share);
  assert.equal(actual.share.state, 'pending');
  assert.deepEqual(actual.notifications.map(item => [item.user_id, item.kind]).sort(), [['owner', 'returned'], ['reviewer', 'resubmitted']].sort());
  assert.equal(actual.share.reviewer_id, 'reviewer');
  await nativeAction('reviewer', main, 'return_share', 'reason', reasonTwo);
  actual = facts(main.share);
  assert.equal(actual.share.return_reason, reasonTwo);
  assert.equal(actual.share.supplement_text, '');
  const latest = await open('owner', main);
  assert.equal((await latest.locator('.application-panel').innerText()).includes(reasonOne), false);
  assert.equal((await latest.locator('.application-panel').innerText()).includes(noteOne), false);
  await nativeAction('owner', main, 'resubmit_share', 'explanation', noteTwo);
  actual = facts(main.share);
  for (const user of ['owner', 'reviewer']) {
    const page = await open(user, main);
    const text = await page.locator('.application-panel').innerText();
    assert.ok(text.includes(reasonTwo)); assert.ok(text.includes(noteTwo));
    assert.equal(text.includes(reasonOne), false); assert.equal(text.includes(noteOne), false);
  }
  assert.deepEqual(actual.journal.map(item => item.after_state), ['pending', 'awaiting_supplement', 'pending', 'awaiting_supplement', 'pending']);
  assert.deepEqual(['file_id', 'owner_id', 'recipient_id', 'reviewer_id'].map(key => actual.share[key]), [main.file, 'owner', 'recipient', 'reviewer']);
  for (const text of [reasonOne, noteOne, reasonTwo, noteTwo]) {
    assert.equal(JSON.stringify(actual.notifications).includes(text), false);
    assert.equal(JSON.stringify(actual.journal).includes(text), false);
  }
  await shot(pages.reviewer, 'reviewer-latest-pair');
  checks.push({name: 'Two actual return/resubmit rounds retain only the latest pair, original participants and text-free state history/notices'});

  await nativeAction('reviewer', main, 'approve');
  const download = await contexts.recipient.request.get(main.download);
  assert.equal(download.status(), 200);
  assert.equal((await download.body()).toString('utf8'), main.content);
  actual = facts(main.share);
  for (const user of ['owner', 'recipient', 'reviewer']) {
    assert.equal(actual.notifications.filter(item => item.user_id === user && item.kind === 'review_result').length, 1);
    assert.equal(actual.notifications.filter(item => item.user_id === user && item.kind === 'shared').length, 1);
  }
  assert.equal(actual.share.revision, 6);
  checks.push({name: 'Final approval retains three-party results/sharing notices and serves the exact uploaded bytes'});

  // Actual accepted boundary: both fields are exactly 200 ASCII characters.
  await nativeAction('reviewer', cancel, 'return_share', 'reason', 'r'.repeat(200));
  await nativeAction('owner', cancel, 'cancel');
  assert.equal(facts(cancel.share).share.state, 'cancelled');
  await denied('owner', cancel, 'resubmit_share', {explanation: noteOne});
  await nativeAction('reviewer', reject, 'return_share', 'reason', 'r'.repeat(200));
  await nativeAction('owner', reject, 'resubmit_share', 'explanation', 's'.repeat(200));
  assert.equal(facts(reject.share).share.supplement_text.length, 200);
  await nativeAction('reviewer', reject, 'reject');
  assert.equal(facts(reject.share).share.state, 'rejected');
  assert.equal((await contexts.recipient.request.get(reject.download)).status(), 403);
  assert.equal((await contexts.recipient.request.get(cancel.download)).status(), 403);
  checks.push({name: 'Exactly 200 characters are accepted; owner cancellation while waiting and rejection after resubmission grant no download'});
  result.nativeFacts = {approved: facts(main.share), cancelled: facts(cancel.share), rejected: facts(reject.share)};

  for (const context of Object.values(contexts)) await context.close();
  const beganStop = Date.now();
  const responsePromise = viewer.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith('/api/recordings/stop'), {timeout: 45000});
  await viewer.click('#record-stop');
  const response = await responsePromise;
  assert.ok(response.ok()); await response.finished();
  result.stopMilliseconds = Date.now() - beganStop;
  const recording = await api('/api/recordings/' + result.recordingId);
  await writeFile(path.join(out, 'actual-recording.json'), JSON.stringify(recording, null, 2));
  result.recordedEvents = recording.events.length;
  assert.equal(recording.status, 'stopped'); assert.deepEqual(recording.gaps, []);
  for (const field of ['errors', 'data_errors', 'dropped']) assert.equal(recording.final.health.producer[field], 0);
  assert.equal(recording.final.health.producer.pending, 0);
  for (const text of [reasonOne, noteOne, reasonTwo, noteTwo]) assert.equal(JSON.stringify(recording).includes(text), false, 'Private text entered observation output');
  for (const node of ['return_share', 'resubmit_share', 'return_notice', 'resubmit_notice']) {
    assert.ok(recording.events.some(event => event.node === node && event.phase === 'enter'), 'No real enter: ' + node);
    assert.ok(recording.events.some(event => event.node === node && event.phase === 'return'), 'No real return: ' + node);
  }
  assert.ok(recording.events.some(event => event.phase === 'change' && event.outputs?.state === 'awaiting_supplement'));
  assert.ok(recording.events.some(event => event.node === 'resubmit_share' && event.phase === 'return' && event.outputs?.reason_length === reasonTwo.length && event.outputs?.supplement_length === noteTwo.length));
  checks.push({name: 'Complete real recording contains the new lifecycle/state/value/notice events and no private text', events: recording.events.length});
  result.passed = !errors.length;
} catch (error) {
  result.passed = false; result.error = String(error.stack);
  await shot(viewer, 'failure').catch(() => {});
  if (started) {
    const state = await api('/api/recordings').catch(() => null);
    if (state?.active) await fetch(observer + '/api/recordings/stop', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}'}).catch(() => {});
    const recording = await api('/api/recordings/' + result.recordingId).catch(() => null);
    if (recording) await writeFile(path.join(out, 'actual-recording.json'), JSON.stringify(recording, null, 2));
  }
} finally {
  await writeFile(path.join(out, 'results.json'), JSON.stringify(result, null, 2));
  await browser.close();
}
console.log(JSON.stringify({passed: result.passed, checks: checks.length, events: result.recordedEvents, error: result.error}));
if (!result.passed) process.exitCode = 1;
