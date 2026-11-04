# Source-graph migration

The new source projection connects authored business and state nodes to unique
physical declarations. All 124 previous nodes remain after complete reconstruction;
102 declarations were added. Application source, executable state transitions,
capacity and join rules, probes and independent expectations match the previous
accepted checkout byte for byte. The legacy discovery format remains in use.

The baseline came from a clean Git HEAD export. Its frozen approval passed
`change_sync check`, then `begin` created a new change before applying the current
runtime and graph changes. Earlier approvals and review records remain intact.

During migration, running the generator without the repository's configured JS
adapter exposed an existing publication bug: it could write a graph after partial
source analysis. Both example generators now reject parser errors before writing.
`missing-adapter-regression.json` records a real failed invocation and identical
graph hashes before and after it. `build.json` records the configured successful
generation. `initial-source-and-model-diff.json` retains the incomplete attempt;
`source-and-model-diff.json` describes the complete result.

Other evidence:

- `baseline-check.json` and `baseline-begin.json`: previous release and new change.
- `initial-inspect.json`: the expected missing-review refusal.
- `seal.json`: managed-copy review.
- `verify.json`, `accept.json` and `check.json`: full independent gates for this candidate.
- `.release/stategraph/concept-models-20261104`: preserved baseline, detailed tests,
  review and acceptance for clean Git exports.

Install the parser once with `python tools/setup_adapters.py`. Repository demo
commands select that installation through `BO_ADAPTER_HOME`; separately copied
examples need the adapter's locked npm dependencies installed locally.

`verify-01-failed.json` preserves the rejected stale source index. The index was
regenerated with the configured parser by `bo_sync scan`; its checks remain
enabled. `final-build.json`, `final-seal.json` and `final-scan.json` record the
rebuild against the final shared runtime. No saved index was removed to make a
validation pass.

The source-graph migration passed mapping, state rules, all project checks and
189 independent business assertions. A separate maintenance change was then opened
from those accepted inputs before updating the recording-version context. Recording
list/detail operations now use lightweight version metadata, while explicit graph
controls retain the complete validated inventory. `recording-context-*.json` holds
the corresponding review and command receipts; the final frozen directory is
`.release/stategraph/concept-models-20261104-recording-context`.

`demo-entrypoint.json` records the successful `python tools/archive_demo.py --verify`
entry point, including accepted-source checks, architecture checks, 13 application
tests and graph history invariants. `frozen-release.json` identifies the preserved
changes and final candidate; `previous-frozen-release/` retains the former rolling
manifest and state metadata.
