/** Real browser users, HTTP permission checks, recording and timeline witnesses. */
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
const { chromium } = createRequire(import.meta.url)('playwright');
const application = process.argv[2];
const observer = process.argv[3];
const phase = process.argv[4] || 'v1';
const out = path.resolve('docs/review/dialogue-acceptance-20261031/operations-' + phase);
await mkdir(out, {recursive: true});
const browser = await chromium.launch({headless: true, executablePath: process.env.BO_BROWSER_EXECUTABLE});
const viewer = await browser.newPage({viewport: {width: 1520, height: 1060}});
const contexts = {};
const pages = {};
const checks = [];
const errors = [];
const result = {phase, application, observer, checks, errors};
const api = async route => {
  const response = await fetch(observer + route);
  assert.ok(response.ok, `${response.status} ${route}`);
  return response.json();
};
const screenshot = (page, name) => page.screenshot({path: path.join(out, name + '.png'), fullPage: true});
async function login(user) {
  const context = contexts[user] = await browser.newContext({acceptDownloads: true, viewport: {width: 1280, height: 950}});
  const page = pages[user] = await context.newPage();
  page.on('pageerror', error => errors.push(user + ': ' + String(error)));
  await page.goto(application + '/');
  await page.fill('input[name="username"]', user);
  await page.fill('input[name="password"]', 'TrialOnly!2026');
  await page.locator('form').filter({has: page.locator('input[name="username"]')}).locator('button[type="submit"],button:not([type])').first().click();
  await page.waitForSelector('#my-files');
  return page;
}
async function uploadAndShare(name) {
  const owner = pages.owner;
  await owner.goto(application + '/');
  const content = Buffer.from('Independent VibeLens browser trial / ' + name + '\n');
  await owner.setInputFiles('input[type="file"]', {name, mimeType: 'text/plain', buffer: content});
  await owner.locator('form').filter({has: owner.locator('input[name="action"][value="upload"]')}).locator('button').click();
  const row = owner.locator('#my-files .file-row').filter({hasText: name});
  await row.locator('summary').click();
  await row.locator('select[name="recipient_id"]').selectOption('recipient');
  await row.locator('select[name="reviewer_id"]').selectOption('reviewer');
  const file = await row.locator('input[name="file_id"]').inputValue();
  await row.locator('.share-form button').click();
  const history = owner.locator('.history-row').filter({hasText: name});
  await history.waitFor();
  const share = await history.locator('input[name="share_id"]').inputValue();
  assert.ok(await history.locator('.badge.pending').count());
  return {filename: name, file, share, content: content.toString('utf8'), download: application + '/download/' + file};
}
async function review(record, action) {
  const reviewer = pages.reviewer;
  await reviewer.goto(application + '/');
  const form = reviewer.locator('#reviews form').filter({has: reviewer.locator(`input[name="share_id"][value="${record.share}"]`)}).filter({has: reviewer.locator(`button[name="action"][value="${action}"]`)});
  await form.locator('button').click();
  await reviewer.waitForLoadState('domcontentloaded');
}
async function ownerAction(record, action) {
  const owner = pages.owner;
  await owner.goto(application + '/');
  const form = owner.locator('.history-row form').filter({has: owner.locator(`input[name="share_id"][value="${record.share}"]`)});
  await form.locator(`button[value="${action}"]`).click();
  await owner.waitForLoadState('domcontentloaded');
}
try {
  viewer.on('pageerror', error => errors.push('graph: ' + String(error)));
  await viewer.goto(observer + '/graph?lang=en');
  await viewer.waitForFunction(() => window.graphDebug?.graph && !graphDebug.layoutBusy);
  await viewer.selectOption('#capture-mode', 'all');
  await viewer.click('#record-start');
  await viewer.waitForFunction(() => !document.querySelector('#record-stop').disabled);
  const started = await api('/api/recordings');
  result.startedRecordingId = typeof started.active === 'string' ? started.active : started.active?.id;
  assert.ok(result.startedRecordingId, 'Start action did not create an active recording');
  for (const user of ['owner','recipient','reviewer','other']) await login(user);
  checks.push({name: 'Four actual authenticated browser sessions', passed: true});
  const stamp = Date.now();
  const approved = await uploadAndShare('approved-' + stamp + '.txt');
  result.approved = approved;
  await pages.recipient.goto(application + '/');
  assert.equal(await pages.recipient.locator('#received').getByText(approved.filename, {exact: true}).count(), 0);
  assert.equal((await contexts.recipient.request.get(approved.download)).status(), 403);
  const csrf = await pages.other.locator('input[name="csrf"]').first().inputValue();
  const forged = await contexts.other.request.post(application + '/', {form: {csrf, action: 'approve', share_id: approved.share}});
  assert.match(await forged.text(), /当前没有|permission|权限/);
  await pages.reviewer.goto(application + '/');
  assert.ok(await pages.reviewer.locator('#reviews').getByText(approved.filename, {exact: true}).count());
  checks.push({name: 'Pending share is hidden and denied; unselected reviewer changes nothing', passed: true});
  // Let an actual pending residency grow; this is not an invented function delay.
  await viewer.selectOption('#analysis-view', 'states');
  await viewer.waitForFunction(() => !graphDebug.layoutBusy);
  if (await viewer.locator('.trace-scope').count()) await viewer.selectOption('.trace-scope', 'all');
  await viewer.waitForTimeout(1400);
  result.waitingTimeline = await viewer.evaluate(() => graphDebug.timeline);
  await screenshot(viewer, 'actual-pending-timeline');
  await review(approved, 'approve');
  for (const user of ['owner','recipient','reviewer']) {
    await pages[user].goto(application + '/');
    assert.ok(await pages[user].locator('#messages .message').filter({hasText: approved.filename}).count() >= 2);
  }
  const download = await contexts.recipient.request.get(approved.download);
  assert.equal(download.status(), 200);
  assert.equal((await download.body()).toString('utf8'), approved.content);
  const recipient = pages.recipient;
  const oldLink = recipient.locator(`#received a[href="/download/${approved.file}"]`);
  assert.equal(await oldLink.count(), 1);
  await screenshot(recipient, 'recipient-with-original-link');
  await ownerAction(approved, 'revoke');
  assert.equal(await oldLink.count(), 1, 'Recipient page remains unchanged');
  assert.equal((await contexts.recipient.request.get(approved.download)).status(), 403);
  checks.push({name: 'Actual approval, three-party messages, exact bytes and immediate old-link revocation', passed: true});
  const rejected = await uploadAndShare('rejected-' + stamp + '.txt');
  result.rejected = rejected;
  await review(rejected, 'reject');
  assert.equal((await contexts.recipient.request.get(rejected.download)).status(), 403);
  await pages.recipient.goto(application + '/');
  assert.equal(await pages.recipient.locator('#received').getByText(rejected.filename, {exact: true}).count(), 0);
  for (const user of ['owner','recipient','reviewer']) {
    await pages[user].goto(application + '/');
    assert.ok(await pages[user].locator('#messages .message').filter({hasText: rejected.filename}).count() >= 1);
  }
  const cancelled = await uploadAndShare('cancelled-' + stamp + '.txt');
  result.cancelled = cancelled;
  await ownerAction(cancelled, 'cancel');
  assert.equal((await contexts.recipient.request.get(cancelled.download)).status(), 403);
  await pages.reviewer.goto(application + '/');
  assert.equal(await pages.reviewer.locator('#reviews').getByText(cancelled.filename, {exact: true}).count(), 0);
  checks.push({name: 'Actual rejection and cancellation grant no access', passed: true});
  const message = pages.recipient.locator('#messages .message').filter({hasText: rejected.filename}).first();
  await message.locator('button[value="read_notification"]').click();
  const missingFile = 'missing-file-' + stamp;
  const notFound = await contexts.recipient.request.get(application + '/download/' + missingFile);
  assert.equal(notFound.status(), 404);
  result.notFound = {file: missingFile, httpStatus: notFound.status()};
  await pages.owner.goto(application + '/');
  await screenshot(pages.owner, 'owner-final');
  await screenshot(pages.reviewer, 'reviewer-final');
  // Close application pages before observer-isolation checks to avoid real app reads.
  for (const context of Object.values(contexts)) await context.close();
  await viewer.waitForTimeout(800);
  const stopStarted = Date.now();
  const stopResponse = viewer.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith('/api/recordings/stop'), {timeout: 45000});
  await viewer.click('#record-stop');
  const stopped = await stopResponse;
  assert.ok(stopped.ok());
  // Wait for the actual acknowledgement, then read the saved resource normally.
  // CDP may evict a large response body while live polling continues.
  await stopped.finished();
  result.stopAcknowledgement = {status: stopped.status()};
  result.stopMilliseconds = Date.now() - stopStarted;
  await viewer.waitForFunction(async () => {
    const state = await (await fetch('/api/recordings')).json();
    return state.active === null && document.querySelector('#record-stop').disabled;
  }, null, {timeout: 45000});
  const records = await api('/api/recordings');
  assert.ok(records.recordings.some(record => record.id === result.startedRecordingId));
  const recordId = result.startedRecordingId;
  const recording = await api('/api/recordings/' + recordId);
  result.recordingId = recordId;
  result.recordedEvents = recording.events.length;
  result.recordingStatus = recording.status;
  result.recordingGaps = recording.gaps;
  await writeFile(path.join(out, 'actual-recording.json'), JSON.stringify(recording, null, 2));
  assert.equal(recording.status, 'stopped', 'Capture did not finish cleanly: ' + recording.gaps.join('; '));
  assert.deepEqual(recording.gaps, [], 'The complete recording contains capture gaps');
  await viewer.selectOption('#record-list', recordId);
  await viewer.waitForFunction(() => !document.querySelector('#replay').hidden);
  await viewer.selectOption('#replay-grain', 'events');
  await viewer.selectOption('.trace-scope', 'all');
  await viewer.click('.trace-fit');
  await viewer.click('.trace-maximize');
  await viewer.waitForFunction(() => graphDebug.timeline?.geometry?.plot > innerWidth - 300);
  result.timeline = await viewer.evaluate(() => graphDebug.timeline);
  const missingEntry = recording.events.find(event => event.node === 'download' && event.phase === 'enter' && event.inputs?.file_id === missingFile);
  assert.ok(missingEntry, 'The actual not-found download has no captured entry');
  const missingInterval = result.timeline.lifecycles.find(interval => interval.node === 'download' && interval.entryEventId === missingEntry.id);
  assert.ok(missingInterval, 'The actual not-found download has no lifecycle projection');
  assert.equal(missingInterval.unfinished, false, 'An actual exception exit was left running');
  result.notFound.lifecycle = missingInterval;
  result.notFound.semanticLabelCorrect = !missingInterval.stages.some(stage => stage.registered && /denied|rejected|拒绝|驳回/i.test(stage.label));
  assert.ok(result.timeline.lifecycles.some(interval => interval.end > interval.start), 'No actual lifecycle duration');
  assert.ok(result.timeline.routes.length > 0, 'No actual causal connector in this recording');
  assert.ok(result.timeline.routes.some(link => link.fromRow !== link.toRow), 'No cross-node or cross-layer handoff');
  await screenshot(viewer, 'actual-duration-and-connections');
  checks.push({name: 'Saved actual recording contains durations and directed handoffs', passed: true,
    events: recording.events.length, intervals: result.timeline.lifecycles.length, routes: result.timeline.routes.length});
  assert.equal(result.notFound.semanticLabelCorrect, true, 'A missing file was relabeled as a permission denial using only its broad exception class');
  checks.push({name: 'A specific domain outcome is not inferred from a broad exception type', passed: true});
  result.passed = !errors.length;
} catch (error) {
  result.passed = false;
  result.error = String(error.stack);
  await screenshot(viewer, 'failure').catch(() => {});
  console.error(result.error);
} finally {
  await writeFile(path.join(out, 'results.json'), JSON.stringify(result, null, 2));
  await browser.close();
}
console.log(JSON.stringify({passed: result.passed, checks: checks.length, events: result.recordedEvents, error: result.error}));
if (!result.passed) process.exitCode = 1;
