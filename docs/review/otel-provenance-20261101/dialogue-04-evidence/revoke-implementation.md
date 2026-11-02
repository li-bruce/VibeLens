# Designated share revocation

## Confirmed scope

The actual user asked for immediate uploader revocation of active or waiting
sharing, no reactivation by an old delayed notification, and a revocation message
to the same recipient. The user explicitly confirmed that administrator access
remains independent and approved the focused graph. Original dialogue is retained
in `revoke-dialogue.md` and `discovery.json`.

## Native behavior

The existing native `bo.fsm` executor gains `revoke` transitions from
`share_notice_wait` and `active_share` to terminal `revoked_share`. The uploader's
transaction updates the share, cancels waiting original share jobs, and inserts
a revocation notice job. A failed outbox insert rolls the entire transaction back.
Committed revocation takes effect before notification delivery. Repeated revocation
returns the same notice job without creating another message or transition.

The worker re-reads the actual job inside its `BEGIN IMMEDIATE` transaction. A job
prefetched before revocation cannot activate a cancelled share afterward. A second
state check prevents grant activation unless the share still waits for its first
delivery. Revocation notice delivery only inserts the message and completes its
own job; it never executes a grant transition. Failed delivery leaves the share
revoked and the notice waiting for retry. New download and information requests
use the current native access rule even when the recipient page is stale. An
already authorized response is not a mechanism for recalling bytes already sent.

Revocation removes only the specified grant. Other recipients and independent
uploader/administrator access retain their existing rules. This iteration does not
add a second share after revocation; the existing unique file/recipient rule remains.

## Source and observation

The owner form posts to `/command/revoke`; the native JSON boundary is
`POST /api/files/<file_id>/revoke` with `recipient_id`. Both reuse upstream Flask
instrumentation, real WSGI comparisons, SDK identities and existing API nodes.
`revoke_share`, `revoked_share` and `deliver_revoke_notice` retain the business
identities from the confirmed design. Native SQLite commits, rollback, rules,
state journal and selected actor/file/share/job/message facts remain distinct.

SQLite version 3 broadens the shares/jobs checks in a native transaction while
preserving every row and reference. The project runtime was backed up to
`pre-revoke/runtime-before-migration.sqlite3`; no other project was touched.
The legacy source schema remains a tracked test fixture. Tests exercise successful
and repeated migration, injected migration rollback, terminal state rejection,
and missing/wrong state-witness negative controls.

## Retained development findings

- `revoke-model-failure-01.json` preserves a project generator failure: discovery's
  `event` relation was passed directly to a runtime graph accepting `flow` for this
  asynchronous progression. The authored link now uses `flow` with its delayed-job
  label; native queue causality remains SDK-linked evidence. No validator was changed.
- The temporary sandbox design service printed a URL but did not respond across
  the command boundary. That URL was not delivered as a verified live graph. The
  accepted application/graph service will be restarted and checked for handoff.
- `revoke-focused-unit` and `revoke-pending-first-run` retain focused passing checks
  before the full runtime matrix.
- `revoke-sharing-attempt-01` passed business, state and project checks but failed
  mapping: the project generator incorrectly declared a state-change `instance_id`
  on `deliver_revoke_notice`. That worker only sends a message and reads the already
  revoked share state. The new node's declaration was corrected without inventing
  a state change or altering any earlier capture, contract or validator.

- `revoke-sharing-attempt-02` passed mapping, business and state checks. Its project
  test selected a genuine earlier-build revoke job, but the older test searched
  only review/share worker nodes. It now checks the exact node for the native
  job kind, including revoke, retaining strict old-build rejection, source links,
  current build/actor checks and zero normal observation errors. The failure and
  its complete check receipt are retained. Future attempts archive every check
  receipt before another run can replace the active work directory.

## Verification scope

Retain all 11 earlier scenarios and on/off/fault modes, adding four revocation
scenarios. Compare current native HTTP results, current principal/object context,
state instances/journal, database effects, lifecycle closure and real producer
health. The parent conversation owns independent browser acceptance.

## Accepted result

`revoke-sharing-attempt-03` passed the complete canonical scan, inspect, verify,
accept and check sequence. Mapping, state rules, business and project checks all
passed. The runtime matrix has 15 scenarios and 45 on/off/fault runs. Independent
readers compared 103 native HTTP responses, including 58 revocation-case requests.
All normal probe/data error and drop counters are zero. Twelve project tests passed,
including migration rollback and deliberately missing/wrong revocation witnesses.
The earlier 18 acceptance files and all 138 copied canonical runtime files remain
unchanged. Full receipts are archived with the successful attempt.

`revoke-acceptance-summary.json` records the accepted candidate/build. The restarted
application remains at `http://127.0.0.1:50949`; its graph is
`http://127.0.0.1:50950/graph`. Read-only HTTP checks confirmed both URLs, the public
export, current source binding, new graph nodes and the exact accepted build.
`revoke-service-handoff.json` records the native process and health. The initial
handoff check mistakenly treated the historical discussion-focus snapshot as the
implementation inventory; the corrected check uses `/api/view.model.nodes` and
requires no source or business change. Browser acceptance has not been run here.
