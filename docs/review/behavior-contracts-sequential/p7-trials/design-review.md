# Initial design review

This is an interim evaluator record. Neither application has completed native
implementation or acceptance. Questions still open in a draft are pending work,
not automatically missing-model defects.

| Observation | Evidence | Current interpretation |
|---|---|---|
| Both chats asked drive/observe and permission questions before coding | Exported dialogue, replies 01 | Correct mode-independent start; choices differ intentionally |
| Python distinguished queued work from work already started | Python reply 01 | The simulated user corrected “transmission starts” to “worker starts preparing”; inspect the eventual read/completion boundary |
| Node retained queue-time authorization after revocation | Node reply 02 | A valid different policy, not a missed permission recheck |
| Node offered seeded accounts versus real login/account management | Node reply 03 | The alternatives conflated data seeding, authentication and administration; user clarification retained real password sessions with seeded users |
| Python sent its first question batch twice before the answer arrived | Actual question tool records | Dialogue usability defect; existing `asked_in`/awaiting-answer scheduling was not used consistently. Assess the maintained guidance before a final fresh trial |
| Draft schema and bilingual labels were checked before Web review | Each trial's `review/` receipts | Structural checks only; no implication of user confirmation or native evidence |
| Local viewer startup/browser access encountered host errors | Trial command/tool records | Retain failed attempts. HTTP availability, browser rendering and graph meaning are separate checks |

Final review must compare the actual presented graph, recorded confirmation and
implemented behavior. The announcements board remains an independent capability;
authentication may be shared without inventing a single route through both apps.
Do not infer a missing feature from a focused preview that explicitly retains it
outside the shown boundary. Conversely, a full-scope confirmation must not silently
accept that omitted boundary.

## General repair before native implementation

Both coding chats were asked to stop at their current design and retain unanswered
questions. No application implementation was accepted. The following repairs are
in the canonical package, not hand-edited installed copies:

- A new design starts with its business view (or the first applicable state/rule
  view). Existing saved selections remain authoritative. The complete models stay
  available through ordinary view and layer controls.
- Conversation previews and model-review workbooks resolve the installed semantic
  names in the requested locale. Focus IDs, semantic snapshots and confirmation
  scopes are unchanged; missing translations keep the authored fallback.
- Dialogue guidance explicitly distinguishes asynchronous delivery acknowledgements
  from answers and keeps independent choices out of false either/or options.

`preview-before.log` reproduces missing Chinese captions. `default-view-before.log`
is the new first-view regression before its implementation. `preview-second.log`
passes 40 related cases. `design-node-second` retains the original unreadable
combined view; `design-browser-fix-second` retains English/Chinese 2D/3D business
views and restored state selections with zero runtime events.

The first browser capture timed out waiting for network idleness on a polling
viewer. Its raw HTTP snapshots and error remain in `design-node-first`. The
capture now waits for graph layout readiness. The first repair browser run checked
the controls, but its 3D screenshot preceded routing completion; the second waits
for both geometry and routing before capturing. Neither harness change weakens a
runtime or business assertion.

The repository owner subsequently answered earlier Node question cards, selecting
drive and answering an either/or revocation question with “是”. The coding chat
correctly retained the ambiguity instead of guessing. The owner then explicitly
restored Node observe in the coordinating chat; `node-reply-04.json` distinguishes
that real instruction from the remaining simulated application answers.

The full regression then found two maintenance-test assumptions in
`test_behavior_plan.py`: the test expected P6 to remain incomplete forever, and
its single fake receipt replaced evidence for every already-passed case. The
tests now explicitly set the missing prerequisite and override only their own
receipt. The production ledger checker and all rejection assertions remain
unchanged. `repair-01/full-verify.log` retains the failure;
`ledger-fixture-retest.log` records eight passing tests before the full rerun.

The related 154-test run also hit a Windows sandbox denial while creating a
directory junction. Its unchanged host-permission retest passed. This is distinct
from the unavailable file-symlink privilege retained in the P6 full-suite report.
