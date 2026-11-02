# Acceptance scope

## Evidence classes

The full repository command, shipped-example acceptance, independent application
acceptance and actual browser interactions are separate results. None substitutes
for the others. Dialogue answers in the independent trial are simulated by the
coordinating AI under the human's instructions; they are not human usability data.

The repository's latest complete gate is
[`repository-verification-11.json`](repository-verification-11.json). It passed
`tools/verify.py --database` on November 1 at 04:21:47 +08:00. The canonical SDK
selection hash is recorded there. Subsequent review helpers and application-only
iterations do not change those SDK bytes.

## Layers

| Layer | Inspect directly | Runtime claim |
| --- | --- | --- |
| Business | Confirmed operations, requirements and source bindings | Actual operation entry, values and exit in the stopped recording |
| State | Native machine states/transitions, graph state counterparts | Entity/revision-specific state frames and the native transition journal |
| Rules | Shared policy nodes and operation outputs | Captured inputs, evaluations and actual enclosing invocation |
| API | Native route registrations, handler references and parameter sources | Actual request responses and captured boundaries, checked separately |
| Operations | Declared queries, transformations and transaction targets | Native SQLite calls, commit/rollback, parameters and real parent calls |
| Execution | Bound functions and configured key values | Only explicitly captured calls/values; static functions are not counted as executed |
| Project | Files, directories and containment/import references | Static inventory; no artificial file-activation events |
| Code | Function/class/parameter declarations and static calls | Static source facts with unresolved references retained explicitly |
| Data | ORM declarations and the inspected native database structure | Structure is static; actual data processing belongs to the operation recording |

For accepted withdrawal build details, see
[`dialogue-11-independent-v2/summary.json`](dialogue-11-independent-v2/summary.json).
It freezes exact accepted source bytes and independently checks native literal
route registrations, state values, static endpoints and original event owners.
The same review for the rejection-reason iteration is in
[`dialogue-11-independent-v3/summary.json`](dialogue-11-independent-v3/summary.json).
No prior capture fields, features or feature-case clauses were removed.

## Definitions and invocation ownership

A node's identity, capture fields, types, source binding and lifecycle are defined
before acceptance. Actual values and invocation identities come from execution.
The earlier ordinary-point capture defect omitted actual parent-call metadata;
that is a shared capture/checking defect, not an expected class of observations.
Strict complete acceptance now rejects it even when business responses are right.

A supplied parent-entry ID whose target lies outside a retained history window is
a different condition. A partial recording discloses that missing boundary.
Original source, timestamps, matching file IDs and AI text never replace it.
See the focused [explanation](observation-ownership-explanation.md).

## Boundaries of these results

- The 20,000-event benchmark measures Canvas Timeline presentation, not the cost
  of scanning a whole application or instrumenting every function.
- The retained 15-suite browser matrix includes two failed synchronization checks
  and their targeted retests. It is not one uninterrupted all-green run.
- The file-sharing application exposes two blocked 3D self-relations in orthogonal
  and bus routing. Straight and curved routing remain available; the recording
  and these limitations are preserved in the application evidence.
- Bounded history, queue overflow, stop timeout and missing pre-start parent
  targets are disclosed. Successful later recordings do not erase failed ones.
  In particular, the final-build rapid-list process dropped 2,701 events. Its
  failed health guard and raw evidence remain; a later same-build process is
  separately identified and cannot make the lost capture complete.
- Python drive-mode application acceptance does not establish independent
  end-to-end acceptance for every language or framework. Native Node adapter and
  shared-protocol regressions have their own component evidence.
- No GitHub commit, push, merge, release or Pages deployment is performed here.
