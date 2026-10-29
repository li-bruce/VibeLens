# Initial version acceptance

Date: 2026-10-29 (Asia/Shanghai).

Status: initial application implemented and automated trial checks passed. The requirement confirmation was explicitly simulated by the main chat; this is not independent human or production acceptance.

## Frozen identities

- Canonical Skill revision: `e69ce0921ac06fb455ec0aedc403e24d74babebc`.
- Current accepted candidate: `de568f8032081e09018f41908949af30c344eea3526db17bae16a258f218f18f`.
- Running build: `dcfbd2284f39b12a659a00e1cb707ce3235b19dae4252cd495b2c62cd25d2d7e`.
- Original immutable baseline SHA256: `8339139b0637be9abdea6611a1952bccce286954ea2ceca351ec0293456c79f7`.
- Original accepted implementation: `.stategraph/initial-v1/`.
- Current technical browser-evidence follow-up: `.stategraph/initial-v1-browser-evidence/`.
- Stable project identity: `file-sharing-stable-trial-20261029`.

The technical follow-up corrected only browser evidence selection/readiness. Its baseline was the accepted initial implementation; neither baseline was reset. Business behavior, independent expected outcomes, and the 37-file exported core remained unchanged.

## Application scope

Python/Flask, SQLite/SQLAlchemy Core, and server-rendered lightweight HTML/CSS. The native `bo.fsm/1` executor runs from the declared state machine. The shared native policy evaluator supplies the decision used by the application.

All three seeded users can own files they upload. The example flow uses 林舟 as owner, 许宁 as recipient, and 周岚 as an unrelated user. Only the owner shares; owners and selected recipients can inspect metadata and download. Recipients cannot reshare or edit. No registration, preview, editing, deletion, revocation, teams, public links, approvals, subscriptions, or promotion-material export was added.

## Results, kept separate

| Category | Result | Evidence |
|---|---|---|
| Implementation mapping | Passed: 14 features; 264 witnesses and 315 projection checks; actual policy/data evidence and both public exports validated | `change-verify-final.json`, `evidence-checks.json` |
| State constraints | Passed: real initial pending capture and upload/private, share/shared transitions; raw storage journal retained and compared | `runtime-observations-final.json`, browser recording, `evidence-checks.json` |
| Business rules | Passed: 60 actual scenario/mode runs and all 78 required assertions | Current change's `checks/observations.json`, `change-verify-final.json` |
| Project checks | Passed: 24 pytest cases, static architecture guard, canonical managed-copy parity, accept/check | Current change's `checks/test-0.json`, `architecture-final.json`, `change-check.json`, `canonical-parity-plan.json` |
| Browser/UI | Passed in headless Chromium: three identities, upload, owner-only share, exact download bytes, unrelated-user rejection, locale switch, narrow browser viewport, source/query exclusion, recording, exact-event replay, actual rendered reload | `browser/20261029T023804Z-df231d/report.json` and screenshots |
| Observer isolation | Passed with observation on/off/failing; queue-limited business behavior passed; exported core ran without observer imports | Project tests and `core-reproduction.json` |

The final offline observation run contains 1,335 real events in enabled mode. The final browser recording contains 502 real events, zero gaps, and three exact state frames: `pending`, `private`, `shared`. The browser verified the exact upload and share event IDs and each corresponding active state. Page and console errors were zero. The measured final capture-drain wait was 44.918 seconds; application commands do not wait for this observer queue.

## Evidence sensitivity and schema checks

Six checks passed. These modify only in-memory evidence or verified temporary copies, never the application:

1. Missing download capture field is rejected.
2. Incorrect captured download size is rejected against independent HTTP bytes.
3. Missing exported instance is rejected.
4. An unsynchronized source comment in an isolated source copy is stale.
5. A real SQLite column rename in an isolated database is detected against native declarations.
6. A removed actual transition frame is rejected by the independent transition-path assertion.

Both the app and observer public exports passed the canonical export validator. The original baseline hash remained unchanged.

## Recording, reload, and core reproduction

- The live development launcher was observed restarting both observer and producer after a manifest build change.
- Actual build reload hid old-version recordings from the current list and preserved both existing preference entries. Historical recording files were retained.
- The 196 managed runtime/viewer/core files matched their installed hashes, the canonical upgrade plan had zero changes/conflicts, and the native executor matched canonical bytes.
- `dist/core-initial-v1.zip` contains 37 files. It was extracted to a checked temporary project directory and representative login/upload/share/download/denial behavior ran with observer modules absent. Its included bytes were compared against the final project and matched. The temporary extraction was removed; the ZIP and reproduction report remain.
- Core archive SHA256: `6123334473b86192e07787c279d9616ac253673d2691b0441aee0d6bdc495a80`.

## Failure and correction history

- Restricted Python ensurepip and default temporary directories failed because of local process/filesystem restrictions. A local environment and project-contained test directories resolved those setup failures. `pytest-first.txt` preserves the initial test result.
- Initial design-only declarations were not valid executable runtime declarations. The project adopted supported node types and native enum/state fields; no canonical validator was changed.
- Policy projection was stabilized with explicit real predicate anchors and canonical generation order.
- Browser attempt `20261029T020913Z-202a54` reached actual application effects but failed a 10-second queue-drain assertion. Later inspection found 279 actual events and zero errors/drops/gaps. The failed report and late-drain completion are retained.
- Browser attempt `20261029T021652Z-f92e69` exposed an activity/file-state journal shape mismatch in the project adapter. Raw file-state history was retained under `state_journal`, native transition witnesses were mapped explicitly, and real initial state capture was added. The canonical viewer was not patched.
- Browser attempt `20261029T022419Z-91395b` passed. Screenshot review then found a harness event-index assumption and an insufficient reload-render wait. A separate technical change used the canonical timeline and exact event IDs, and required semantic graph readiness. Final attempt `20261029T023804Z-df231d` passed.
- The auxiliary evidence-audit script initially used an incorrect return-type assumption and report path. Both harness errors were corrected; the six checks then passed for the final build.

## Boundaries

These are finite automated synthetic-data checks. Static inventory retains 356 unresolved library/dynamic-call candidates as unknowns; they are not asserted to be observed calls or complete semantic proof. Captures exclude passwords, session tokens, and file bodies. The local Flask server is a development launcher, and no production deployment or human acceptance is claimed.

The application database contains synthetic browser trial files. No other trial directory or source-chat history was inspected. No maintained canonical source was changed, no other chat was contacted, and nothing was pushed to GitHub.

## Reproduce and next step

Start both services with `.venv/Scripts/python.exe -B -X utf8 run.py`. App: `http://127.0.0.1:8840`; graph: `http://127.0.0.1:8841/graph`.

Run `tooling/check.py`, `review/browser_acceptance.py`, and `review/evidence_checks.py` with that Python environment. See the linked English/Chinese README for setup and account details.

Stop at this initial version and wait for the next user iteration. Revocation, including refusing a subsequent download from an unrefreshed recipient page, remains deferred.
