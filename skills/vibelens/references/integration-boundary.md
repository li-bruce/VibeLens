# Application and framework ownership

Use the installed Skill as the tool provider. Run its scripts with `--root PROJECT`.
The application owns its business/state/rule definitions, native execution,
selected probe wiring and tests. The Skill owns analysis, projection, recording,
layout, viewer code and control validation.

The renderer, routing libraries (including libavoid), layout engines and Web
assets are local debugging-tool dependencies. New integrations do not copy them
into the business project or its production bundle. Native state/probe adapters
are separate, small project dependencies. Historical full-copy examples retain
explicit viewer folders until a reviewed migration.

This deployment boundary does not change third-party licenses. The intended use
is local development/debugging; commercial application development is allowed by
VibeLens's MIT license. Distributing an embedded viewer is a separate packaging
choice. See [dependency distribution](dependency-distribution.md).

## New integrations

```bash
python SKILL/scripts/bo_integrate.py plan --root PROJECT --language python
python SKILL/scripts/bo_integrate.py apply --root PROJECT --language python
python SKILL/scripts/bo_integrate.py check --root PROJECT
python SKILL/scripts/bo.py serve --root PROJECT --port 8830
```

Use `--language javascript` for Node, React and Vue. Python copies seven small
standard-library native files; JavaScript copies two native modules. These are
managed dependencies under `bo_stategraph/`, with `integration.json` recording
their exact source and hashes. The independent state definition stays in
`project.json` or the project's established `machine.json`. Choose optional
database/policy/OTel adapters from the installed package when required; do not
recreate a parser, evaluator, protocol validator or viewer in application code.

Do not automatically migrate an existing full-copy installation. Keep its
working contract and use `bo_upgrade plan/apply`; then run normal acceptance.
The new lightweight path does not delete legacy runtime folders or change
application imports behind the developer's back.

## Communicate through native adapters

The `bo-event/v1` and model-qualified `bo-snapshot/v2` contracts carry actual observations (legacy single-model snapshots retain v1)
to the external Python service. Native business effects and drive-mode state
transitions execute locally, including when the service is unavailable.

Connect remote recording controls once, in the isolated observation bootstrap:

```python
from bo_stategraph.bo_capture import BOCaptureClient

bo_capture = BOCaptureClient(bo_probe).start()
# On observer integration shutdown: bo_capture.close()
```

```javascript
import { BOCaptureClient } from './bo_stategraph/bo_capture.mjs';
const boCapture = await new BOCaptureClient(boProbe).start();
// On observer integration shutdown: await boCapture.close();
```

Startup registration reports connection/configuration failures. An optional
observer bootstrap may catch that failure, record observation as unavailable,
and continue native application startup. Do not turn unavailable monitoring into
a successful capture check.

`bo-capture-control/v1` uses authenticated local HTTP, pinned project/build and
producer identities. Producers pull only `scope` and `flush` commands and return
actual queue health. Register every producer before recording. Start/stop waits
for all registered producers; a missing acknowledgement records a gap. Hot reload
creates a producer for the new build. Control traffic creates no business events.
Keep installed packages and `bo_` wiring excluded from automatic instrumentation.

## Agent editing boundary

During business coding, edit project declarations, integration wiring and tests.
Read framework APIs as needed; do not patch or monkeypatch installed framework
source, copied native dependencies, validators or generated viewer assets. An
unsupported integration needs a framework fix in its own repository, with a
reproduction; do not replace a check with a permissive application-local copy.

`recall`, source inventory, inspection and acceptance retain the framework receipt
and integrity result. Edited, missing or outdated dependencies require a reviewed
upgrade. Rewriting a native receipt's hash cannot authorize changed framework
bytes; comparison also uses the installed canonical source. Legacy receipts gain
canonical source mappings on their next managed upgrade.
When invoking a legacy project-local CLI, set `VIBELENS_SKILL` to the installed
Skill directory. Existing launchers may supply its `BO_ADAPTER_HOME` instead.
The copied runtime cannot use itself as the independent canonical provider.

`/vibelens` uses `bo_control.py` and its validated view/replay specifications.
It can change presentation choices and replay selection, never source, executable
declarations, raw recordings, required probes or acceptance cases. Other hosts
pass `--host HOST_ID --conversation ACTUAL_HOST_CHAT_ID`; that host namespace
does not share Codex or Harness activation. The host must supply the actual user
message and chat identity. If unavailable, keep conversation controls pending.

These checks are not an OS sandbox. An agent given unrestricted access can edit
the installation or forge host input. To enforce that stronger boundary, the AI
host must keep the installed Skill read-only and expose its control CLI/service
separately. VibeLens does not silently change the host's permissions.
