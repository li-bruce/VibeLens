/** Open the retained real recording in the canonical viewer, without running the app. */
import {gunzipSync} from 'node:zlib';
import {readFile, mkdir, mkdtemp, writeFile, realpath, rm} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {serveRecording} from '../../../../tools/recording_browser_fixture.mjs';

const root = fileURLToPath(new URL('../../../../',import.meta.url));
const validation = path.join(root,'.validation');
await mkdir(validation,{recursive:true});
const temp = await mkdtemp(path.join(validation,'review-recording-'));
const source = new URL('../operations-v1-repaired-boundaries/actual-recording.json.gz',import.meta.url);
const recording = path.join(temp,'recording.json');
await writeFile(recording,gunzipSync(await readFile(source)));
const fixture = await serveRecording(recording);
console.log(JSON.stringify({url:fixture.url,events:fixture.recording.events.length,
  instruction:'Choose the saved recording in the top recording list. The server replays retained evidence only.'}));
let closing = false;
async function close() {
  if (closing) return;
  closing = true;
  await fixture.close();
  const resolved = await realpath(temp), parent = await realpath(validation);
  if (path.dirname(resolved) !== parent || !path.basename(resolved).startsWith('review-recording-'))
    throw Error('Unexpected temporary review directory');
  await rm(resolved,{recursive:true,force:true});
}
process.once('SIGINT',close);
process.once('SIGTERM',close);
