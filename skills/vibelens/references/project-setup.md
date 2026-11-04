# First project setup

Use this sequence for a new project. The small runnable example in a repository
checkout is `docs/review/concept-models-20261104/trial/project/`; its transcript
records a synthetic developer/user trial, separate from human acceptance.

1. **Confirm meaning before implementation.** Record source scope and the user's
   drive/observe choice. Author `discovery.json`, show business, state and rule
   previews, and record scoped confirmation. The [concept model reference](concept-models.md)
   defines these portable declarations. A source-free draft needs no fake function bindings.
2. **Build the native application and separate observation module.** Keep the
   confirmed object identities, transitions and shared rule meaning. Register real
   source symbols and selected values in `bo_stategraph/project.json`; bind the
   definitions with `model.concepts`. In observe mode, the native implementation
   supplies facts; the observer does not execute a second business decision.
3. **Declare the verification inputs together.** `sync.json` identifies the model,
   manifest, independently inventoried `code_files`, watched adapters/test files,
   `acceptance.json`, a protected `mapping.json`, and actual test commands. Include
   the explicit mode decision, static/runtime probe requirements,
   `require_probe_health`, `require_observation_closure`,
   `require_mapping_witnesses` and source symbol classification. The
   [implementation inventory](implementation-coverage.md) maps every authored
   function to a feature, support declaration or reviewed infrastructure exclusion.
   Put scenario runners under `tests/`; keep business entrypoints in source scope.
4. **Implement independent observations.** An observation command emits the shared
   case/mode JSON: real effects and HTTP responses, captured events, producer health,
   independent native reads, projected instances and the public stategraph export.
   Run `on`, `off` and `fault` against actual application operations. A disabled or
   unavailable observer must leave native effects unchanged. Use the
   [mapping contract](mapping-contract.md) and [validation rules](validation-rules.md)
   for exact fields. Configuration alone is not runtime evidence.
5. **Establish the first executable baseline.** Once the initial project can be
   parsed, run `change_sync begin`. The earlier semantic confirmation remains the
   meaning baseline; an initial begin does not claim a nonexistent previous-code
   diff. Run scan, inspect, review, verify, accept and check. Every later iteration
   starts with recall and begin before edits, including changes to adapters.

Pay particular attention to three native boundaries:

- **Initial and changed states:** read the real pre-operation state and revision.
  A snapshot's evidence event must carry that same revision. Preserve the native
  event and selected payload when a transition occurs; verify intermediate states
  as well as the final database row. A newly observed instance with no earlier
  evidence must retain that gap. Focused capture may omit an evidence event:
  `record()` then returns `None`/`null`, and `snapshot()` returns false without
  sending a fabricated reference. Check that return before marking local
  snapshot initialization complete. Existing capture/transport errors remain
  health failures; an omitted pre-state must not be reconstructed from the end state.
- **Capture fields:** declare fields actually read or returned at each boundary.
  For uploads, an explicit byte count can represent content without collecting the
  file. Verify all declared fields and HTTP error returns; do not reuse a broad
  capture dictionary when most functions never produce those values.
- **Rule evaluation:** observe the native predicate result and visited arguments.
  Preserve short-circuit/skipped conditions. A SQL filter is not evidence that a
  registered Python predicate ran; bind the actual implementation or report the gap.

Keep failed receipts. A changed source, declaration or shared tool during checks
invalidates that candidate. Inspect and verify the current candidate again; never
rewrite the baseline or suppress the freshness check.
