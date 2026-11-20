# Independent trial checks

This checklist belongs to the evaluator. It is not supplied to either coding
chat as application design, implementation or a test oracle. Business answers
remain in the recorded dialogue; new meaning is confirmed before implementation.

## Design and identity

- Compare the actually presented business, state and rule networks with the
  recorded answers and their confirmation scope. Preserve intermediate drafts.
- Keep announcements independent from file sharing. Check separate object and
  model identities for recipient grants, download tasks and announcements.
- Inspect reused authentication/ownership predicates and their argument bindings.
  Sharing a predicate must not share one recipient's grant with another.
- Record pending questions, technical decisions and native-engine limitations
  separately. A readable diagram does not count as a runtime witness.

## Native behavior and observation

- Exercise real login/logout, owner upload, recipient sharing, unauthorized
  visibility/download, owner-only grant changes and editor-owned announcements.
- Python: revoke before worker start and after preparation starts; compare the
  real permission read, task state, stored result and retrieval response.
- Node: revoke after accepted submission; the existing task remains usable and
  a new request fails. Repeat retrieval must not close the accepted task.
- Use two actual users and overlapping task executions. Check invocation,
  model, object, attempt and parent/handoff identities against actual results.
- Establish order-specific cases with actual synchronization boundaries. An
  observed queued state does not prevent the next worker admission. Normal
  background runs retain their schedule and use independently witnessed native
  ordering plus the confirmed rule as the oracle. Keep a per-assertion evidence
  map: an absent branch remains unexercised in that recording and needs separate
  controlled evidence, rather than a retry or a relaxed expected outcome.
- Match HTTP denials/errors, rule input/output, state changes and database effects
  to their captured values and lifecycle intervals. Do not infer missing facts.
- Include rejections before a route handler executes: actual CSRF/origin guards,
  authentication middleware and malformed-body parsing where the app uses them.
  A probe placed only inside the successful handler cannot establish this coverage.
- Confirm observer polling, source viewing and graph controls create no business
  events. Compare observation enabled/disabled/failing behavior where supported.
- Inspect every configured layer, including entrypoints, project files, code
  symbols and storage. Exclude dependencies and installed observer implementation.
- Deliberately remove a required captured fact or alter a required observed value
  in a disposable evidence copy. The applicable checker must reject the mismatch.
  Retain the original recording and identify the altered copy as a negative test.

## Iteration and UI

- Request one business change only after the first implementation is independently
  checked. Review its affected model meaning before coding and preserve unrelated
  models, identities and personal view settings.
- Request one source-only refactor. Require refreshed bindings and runtime checks
  without redundant confirmation of unchanged business intent.
- Check 2D/3D views, expansion, containment, layer filters, source navigation,
  semantic names, custom views, recording, replay and Timeline against the same
  graph and recording IDs. Retain legible desktop screenshots.
- A changed source build must invalidate stale implementation evidence. A label
  or layout change must not invent a changed semantic requirement.

## Delivery

Archive visible dialogue, source/model revisions, actual test results, failures,
repairs and final screenshots. Separate business correctness, mapping coverage,
capture completeness, browser behavior and optional finite-model analysis.
Product scenes must use accepted definitions and actual records; a requested
policy change is described as an iteration, not presented as a discovered bug.
