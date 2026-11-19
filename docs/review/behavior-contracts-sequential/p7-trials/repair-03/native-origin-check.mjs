/** Independent real-request check of the trial's native HTTP capture boundary. */
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const [rootArg, outputArg] = process.argv.slice(2);
const root = path.resolve(rootArg), output = path.resolve(outputArg);
await mkdir(output, { recursive: false });
const sources = ['src/http.mjs', 'src/service.mjs', 'src/store.mjs', 'integrations/bo_observe.mjs', 'bo_stategraph/project.json'];
async function fingerprints() {
  return Object.fromEntries(await Promise.all(sources.map(async relative => [relative,
    createHash('sha256').update(await readFile(path.join(root, relative))).digest('hex')])));
}
const before = await fingerprints();
const load = relative => import(pathToFileURL(path.join(root, relative)).href);
const { Store } = await load('src/store.mjs');
const { FileService } = await load('src/service.mjs');
const { createApp } = await load('src/http.mjs');
const { bo_create } = await load('integrations/bo_observe.mjs');
const project = JSON.parse(await readFile(path.join(root, 'bo_stategraph/project.json'), 'utf8'));
const manifest = JSON.parse(await readFile(path.join(root, 'manifest.json'), 'utf8'));
const store = new Store(path.join(output, 'native', 'application.sqlite'));
const service = new FileService(store, path.join(output, 'native'));
const events = [], requests = [];
const observer = await bo_create(service, root, { project, buildId: manifest.build_id,
  sink: async body => { events.push(body); } });
const server = createApp(service, path.join(root, 'public'), observer).listen(0, '127.0.0.1');
await new Promise(resolve => server.once('listening', resolve));
try {
  const base = 'http://127.0.0.1:' + server.address().port;
  for (const [name, route, options, node, expected] of [
    ['origin-rejection', '/api/auth/login', { method: 'POST', headers: { Origin: 'https://unrelated.invalid', 'Content-Type': 'application/json' }, body: '{}' }, 'api_login', 403],
    ['malformed-json', '/api/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{' }, 'api_login', 400],
    ['anonymous-request', '/api/files', {}, 'api_files', 401],
  ]) {
    const start = events.length;
    const response = await fetch(base + route, options);
    await response.arrayBuffer();
    await observer.probe.flush(10000);
    const returns = events.slice(start).filter(event => event.node === node && event.phase === 'return');
    requests.push({ name, actual_status: response.status, expected_status: expected,
      captured: returns.map(event => ({ id: event.id, call_id: event.call_id, outputs: event.outputs })),
      valid: response.status === expected && returns.length === 1 && returns[0].outputs.status === response.status });
  }
  const after = await fingerprints();
  const result = { scope: 'Independent in-progress native trial diagnostic; not final trial acceptance',
    valid: requests.every(check => check.valid) && JSON.stringify(before) === JSON.stringify(after),
    source_unchanged: JSON.stringify(before) === JSON.stringify(after), before, after,
    build_id: manifest.build_id, requests, health: observer.health() };
  await writeFile(path.join(output, 'result.json'), JSON.stringify(result, null, 2) + '\n');
  await writeFile(path.join(output, 'events.json'), JSON.stringify(events, null, 2) + '\n');
  console.log(JSON.stringify({ valid: result.valid, source_unchanged: result.source_unchanged, requests }));
  process.exitCode = result.valid ? 0 : 1;
} finally {
  await new Promise(resolve => server.close(resolve));
  await service.stop();
  await observer.close();
  store.close();
}
