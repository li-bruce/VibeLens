# Independent file-sharing trial

This is a synthetic user/developer dialogue executed in an isolated Python
project. The user answers were simulated by the trial agent. The application,
HTTP requests, SQLite changes, OpenTelemetry spans and validation receipts are
real. It is not evidence of a human usability study.

The first version shares a file with one colleague. The second version gives
each recipient an independent grant: withdrawing Bob's access leaves Carol's
download available. The application keeps its own Python logic in observe mode.

| Review | Real case/mode runs | Captured events | Native mapping checks | Result |
| --- | ---: | ---: | ---: | --- |
| Initial version | 12 | 700 | 48 | All five reports passed |
| Recipient iteration | 15 | 950 | 105 | All five reports passed |
| Readability maintenance | 15 | 950 | 105 | All five reports passed |
| Focused-capture maintenance | 15 | 950 | 105 | All five reports passed |

Each round ran `verify`, `accept` and `check`. Reports independently cover concept
confirmation/binding, implementation mapping, state rules, business expectations
and project checks. Counts include actual on/off/fault runs; only enabled runs
produce accepted observation events. Each named case repeats a complete isolated
HTTP sequence and then evaluates its own independent expectation.

- [Dialogue and confirmed previews](dialogue.md)
- [Exact counts, build IDs and source hashes](summary.json)
- [Readable final receipts](receipts/)
- [Original evidence archive](raw-evidence.zip), including failed attempts,
  initial and changed declarations, baseline/candidate records, complete actual
  observation payloads, the frozen v1 source and source-inventory memory files
- [Focused-capture maintenance evidence](focused-maintenance-evidence.zip), including
  current-framework reconciliation and the separately begun adapter repair
- [Current runnable project](project/)
- [Portable replay result](portable-replay.json) and [complete replay evidence](portable-replay-evidence.zip)
- [Final runtime recheck](runtime-final-evidence.zip), after the shared recording-query optimization
- [Browser evidence](browser/), recorded separately from Python acceptance

The source archive and project contain no uploaded files, database contents,
environment files, virtual environment, collector token or installed dependency.

## What was exercised

The dialogue establishes object identity, shared owner/recipient predicates and
the active/inactive state declaration before implementation. C1 remains intact
when C2 changes the grant identity from `file_id` to `file_id + recipient_id`.
The old binding is rejected before regeneration. Business and physical source
node identities remain stable across that iteration.

The native application and external adapters then verify:

- Real upload bytes, recipient lists, owner-only sharing/revocation and a fresh
  authorization read for every download, including an old URL after revocation.
- Actual Flask 400, 403 and 404 responses with captured final status and complete
  invocation boundaries. State snapshots include initial, active and inactive
  evidence with the application's revision, event and selected recipient.
- Shared predicate results and arguments from the executed Python functions;
  actual SQL reads/writes and metadata from the native SQLite schema.
- A real v1 SQLite grant survives the v2 schema migration. Bob's later revocation
  does not remove Carol's grant or the uploaded file.
- Business effects remain correct with observation enabled, disabled and with a
  deliberately unavailable observer sink. Graph queries produce no business
  events. Independently queried SQLite rows match public stategraph exports.
- The source inventory, API registration, exact policy projection and concept
  binding checks. Removing a guard or a required fact binding in an isolated
  model copy is rejected.

## Failures and repairs

The original logs are retained inside `raw-evidence.zip`.

| Failure | Repair or interpretation | Retest |
| --- | --- | --- |
| Source enrichment changed an exact policy projection | Fixed canonical source/policy composition; preserved strict projection checks | Both projection orders and repeated enrichment now pass; forged metadata still fails |
| SQLite context managers left file handles open | Native connection lifetime now closes explicitly; independent test readers use `closing` | Windows cleanup and all real HTTP runs pass |
| Initial snapshot omitted its evidence revision | Added the native revision to its actual read event | Snapshot accepted; active/revoked states match SQLite |
| A test assumed an unprefixed collector instance ID | Compared the documented run namespace and native identity explicitly | Intermediate-state checks pass |
| Root-level HTTP test runners were treated as excluded application code | Moved independent HTTP runners into `tests/` | Source-first inventory has no unregistered source or implementation gaps |
| A moved protected test command and a mistaken test import failed | Retained the original protected command; corrected the test's API import | Complete project checks pass |
| Shared framework code changed while verification ran | Preserved the rejected freshness receipts and reran the current candidate | Stable candidates accepted; no baseline rewrite |
| Focused capture omitted a read event but queued its snapshot with a null evidence ID | Python and JavaScript adapters now omit snapshots whose event was not captured; existing capture errors remain visible | Real HTTP share still returns 200; focused recording changes from interrupted/error=1 to stopped/error=0, with 9 events and no gaps |
| The local adapter marked an unrecorded initial state as initialized | Mark initialization only after a snapshot is queued; a selected post-state also establishes the first observed state | After hidden sharing, full capture reads Carol's real active state at revision 1; Bob's already witnessed state is not initialized twice |

The focused-recording failure and retest are retained in
`focused-capture-before.json` and `focused-capture-after.json`. Run
`check_focused_capture.py --project <trial> --skill skills/vibelens --out <receipt.json>`
to repeat the real HTTP check. The three `tests/test_snapshot_scope.py` regressions
also cover failed capture and forged non-null evidence; neither can become healthy
or accepted merely because a snapshot was omitted.
The same-instance scope restoration failure and retest are in
`scope-initialization-before.json` and `scope-initialization-after.json`.

The trial also exposed setup overhead: a new native adapter needs explicit
initial-state evidence, a complete capture contract and implementation inventory.
[First project setup](../../../../skills/vibelens/references/project-setup.md)
now describes that sequence and points to the protocol references.

## Reproduce

From a repository checkout, with Python 3.11 or newer:

```powershell
python -m pip install -r skills/vibelens/requirements.txt
python -m pip install -r docs/review/concept-models-20261104/trial/project/requirements.txt
python docs/review/concept-models-20261104/trial/replay.py --skill skills/vibelens --out .validation/colleague-files-replay
```

Use a new output directory. The replay checks retained source hashes, copies the
project, regenerates source/data mappings and executes the complete strict gate.
It writes its own receipts without changing the historical evidence. Its review
is explicitly a replay of the retained synthetic confirmation.
This command was executed from a fresh directory: all five reports, acceptance
and final consistency checks passed with 15 runs and 950 captured events.
After the final runtime update, the old candidate was correctly rejected as stale.
The same change was inspected, reviewed and fully verified again; its new
[accepted candidate is current](portable-final-freshness.json). The earlier receipt
is retained in `portable-replay-before-runtime-upgrade.json`.

To inspect the same program and graph interactively:

```powershell
python docs/review/concept-models-20261104/trial/run_viewer.py --project .validation/colleague-files-replay --skill skills/vibelens
```

Open the application at `http://127.0.0.1:8920/` and VibeLens at
`http://127.0.0.1:8919/graph?lang=zh-CN`. Select Alice, upload a file and share it
with Bob and Carol. Start recording in VibeLens, revoke Bob in the application,
then switch users and compare their downloads. Stop recording and inspect the
business, state, rule and implementation views with Timeline.

## Limits

This small program uses explicit local test identities, not production login.
The trial independently registers SQL execution, not commit/rollback transaction
nodes; the repository's live-database suites cover those separately. No extra
transformation, async-job, resource or concurrency behavior was invented for this
application. Unsupported dynamic calls remain unresolved in the source index.
Browser results and any isolated identity-mapping fixture are reported separately.
