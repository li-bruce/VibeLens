# Preserve same-version reads and validate observation receipts

Status: focused, source, managed-example, complete regression and clean Git export
checks passed.
This repair does not close P7 native acceptance.

## Failures and causes

The preceding timed Python trial retained all eight native journal transitions,
but four `read` witnesses had no replay frame. A fresh evidence ID made an otherwise
identical complete state differ from the engine's stored observation. The existing
same-version conflict check therefore rejected the read. Separately, the probe
treated HTTP 200 as success without checking `accepted: false` in the body.

`snapshot-reads-first.log` reproduces the read failure. `probe-receipts-first.log`
reproduces ignored negative/missing receipts in both native adapters. Their original
trial evidence remains under `../repair-09/python-timed09-failure.json`.

## Implementation

- `observation/snapshot_reads.py` recognizes a read of the current fully validated
  native state. It requires identical state, context, configuration, build and
  revision, plus `phase=read` and no transition claim. Canonical JSON comparison
  preserves value types. Source, evidence, model, instance and producer checks
  still run first.
- The session retains a separate bounded replay frame for each fresh read. It
  leaves the native engine's observation and transition journal unchanged. A
  retried envelope does not duplicate the frame or its byte count. Conflicting
  content, older revisions and new transitions use the original strict checks.
- Python and JavaScript producers require `accepted: true` for individual HTTP
  event/snapshot deliveries. Negative, malformed or missing receipts become
  capture errors. Legacy local callbacks may return no receipt; explicit local
  rejection is reported.
- Skill guidance explains native revisions, repeated reads and receipt checks.
  Native business state and its executor remain authoritative.

## Regression evidence

`reads-receipts-expanded.log` preserves a new test-fixture error: a manually
assembled envelope used the wrong protocol fields. The corrected test retries an
actual producer envelope. `reads-receipts-expanded-retest.log` records 12 passing
tests, including saved replay frames, two independent models sharing native IDs,
duplicate delivery, exact value types, negative receipts and compatibility.
`reads-receipts-existing.log` records 88 passing existing related regressions.

`source-first.log` preserves a formatter check using the repository configuration;
the initial direct formatting invocation omitted that configuration. Only the
changed JavaScript file needed reformatting. The subsequent source gate is separate.

Transport deadlines, retries, recording limits and native revisions are unchanged.
The timed trial's remaining queue delay and incomplete stop boundary still need
their own measured retest. A unit or full regression pass is not native trial
acceptance.

The first managed-example review found that the archive example's ignored local
active pointer still selected its November 12 baseline. Its frozen release pointer
selected the accepted repair-09 review. The older local review and first failure
logs are preserved. Both examples now start from separate copies of the frozen
repair-09 evidence, followed by the normal inspect/review/verify/accept/check path.
No missing-source check or review assertion was removed.

The first complete run (`full-verify-retest.log`) reached the urllib/OTel exclusion
test and failed because that old HTTP fixture returned an empty 200. The fixture
now validates received event envelopes and returns the actual single-item or
batch receipt shape. Its original span/health checks remain, and an added assertion
requires exactly one entry and one return. The first fixture revision mistakenly
wrapped batch receipts; the new assertion detected the resulting fallback duplicate
(`telemetry-retest.log`). The correct array response passes all 32 OTel tests in
`telemetry-second.log`. Complete verification is repeated separately.

`full-verify-second.log` records the successful complete rerun: exit 0, 101 Python
unittest reports with 1,138 reported tests and one skip, JavaScript checks, and
the pinned TLC 1.7.4/Java 17 integration. Both managed examples preserve native
business source and freeze the accepted round as
`behavior-contracts-p7-repair10-20261120`. The new isolated installation has 456
maintained files matching the candidate byte-for-byte. Native trial acceptance
remains separate.

`python-prior-timing.md` and `python-prior-boundaries.json` preserve the completed
offline diagnosis of the original failed trial. They distinguish captured fields
from source-backed reconstruction. The preferences HTTP 400 body was not recorded;
offline validation reproduces a mismatched saved project ID. The stop watermark
retained 31 unfinished target items: 16 arrived before the recording closed and
15 did not. Later delivery cannot repair that historical recording.
