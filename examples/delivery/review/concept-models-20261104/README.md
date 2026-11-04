# Source-graph migration

The maintained source parser now emits one physical declaration for each mapped
function or class and connects the existing observation nodes to it. This example
was rebuilt from its authored graph generator using the new parser.

The previous accepted checkout was restored from Git HEAD and passed its own
`change_sync check`. A new change was then opened there and its baseline carried
into the working checkout. The previous acceptance record remains intact.

The application source, executable state definitions, business requirements,
capture fields and independent expectations were compared against that checkout.
They are unchanged. All 64 previous graph nodes remain; 53 physical declarations
were added. This legacy example retains its original discovery format.

Review artifacts:

- `baseline-check.json` and `baseline-begin.json`: actual old-checkout commands.
- `build.json` and `source-and-model-diff.json`: complete reconstruction and comparison.
- `initial-inspect.json`: the expected refusal before a candidate review exists.
- `seal.json`: reviewed managed-copy fingerprints, separate from business acceptance.
- `verify.json`, `accept.json` and `check.json`: the new candidate's independent gates.
- The corresponding `.release/stategraph/concept-models-20261104` directory retains
  the baseline, review, individual check outputs and acceptance receipts.

The generator also rejects incomplete source analysis before replacing the graph.
The archive example's sibling record contains the real missing-parser regression.

The retained failed checks exposed three outdated renderer fixtures: the overview
expected business roots only, database writes and transactions lacked their data
roles, and a filtering fixture omitted its function kinds. The corrected fixtures
keep the exact business-root assertion, require the one scanned project root with
its descendants folded, and supply explicit types. The original containment,
filtering and relationship assertions remain in place.

`verify-01-failed.json` and `verify-02-failed.json` preserve the rejected candidates.
`clarification-first-failed.log` and `clarification-02-failed.log` retain the earlier
integration failures. Missing adapter setup was corrected; the standalone state
core's accidental dependency on the observer was repaired in the shared runtime.
`final-build.json`, `final-seal.json` and `final-scan.json` record the subsequent
rebuild rather than replacing old acceptance evidence.

The subsequent dialogue regression reached all clarification-history rejection
checks, then correctly refused a candidate whose shared runtime changed during
verification. `clarification-03-candidate-drift.log` retains that failure. The
fixture copies application source but invokes the repository's shared verifier,
so its runtime fingerprint also requires a stable checkout during the test.
The final stable-checkout regression passed all 13 dialogue, history and execution
steps; `clarification-final-report.json` retains the complete results.

After both examples passed their full gates, a separate maintenance change was
opened from those accepted inputs for the recording-version context fix. Recording
list/detail operations use lightweight version metadata; explicit graph controls
retain the complete validated inventory. The `recording-context-*.json` receipts
record that change. Its frozen directory is
`.release/stategraph/concept-models-20261104-recording-context`; the initial
source-graph migration remains preserved under its own change directory.

`demo-entrypoint.json` records the successful `python tools/demo.py --prepare-only`
entry point. `frozen-release.json` identifies the two preserved changes and the
final accepted candidate; `previous-frozen-release/` retains the former rolling
manifest and state metadata.
