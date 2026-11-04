# Project-owned source boundaries

The initial archive profile visited 34,531 directories. Almost all were generated
scenario records under `review/runtime`, rather than application source or
installed packages. The repair separates source ownership from a soft exclusion
used only for business classification.

## Shared policy

The [source-scope reference](../../../../skills/vibelens/references/source-scope.md)
defines `source_scope.roots` and exact `prune` paths with a `dependency` or
`artifact` category and a reason. Initial Skill guidance records source and output
locations with the directory plan. Subsequent batches restore that declaration
and review new directories, outputs, dependency changes and Git ignore changes.

| Content | Treatment |
| --- | --- |
| Owned backend/frontend, local modules, handlers, models, migrations | Discover and check independently of existing graph nodes. |
| Installed dependencies and classified generated outputs | Stop at their boundary before traversal or AST parsing. |
| External imports | Retain the existing import/call boundary; do not recursively index installed packages. |
| `.gitignore` | Hash as an advisory scope input; changed ignore rules require another scope review. |
| Existing soft `exclude` entries | Retain hidden implementation and entrypoint inspection. |
| Watched evidence, configuration and managed-file hashes | Keep byte integrity without treating every watched file as executable source. |

Full-project stategraph acceptance retains the original `.` root requirement.
Additional roots may restore an explicitly owned subtree inside an otherwise
pruned dependency/output path. The default does not prune ordinary directories
named `modules`, `data`, `runtime` or `review`.

Source indexing, API discovery, explanations and project-tree enumeration use the
same policy. Physical execution bindings into pruned storage fail before parsing.
The six protected state/engine source files remain covered by the release gate.

## Checks and measurements

[The 21-test host run](../source-scope-final-regressions.json) checks pruning
before descent, supported owned languages, new top-level source, local overrides,
invalid declarations, links/junctions, direct scans, source/parameter/policy/
telemetry bindings, `.gitignore` snapshot/maintenance invalidation and preservation
of earlier returned graph snapshots. Original tests remain in place.

[Actual archive samples](archive-profile-01.json) visited 56 directories and
retained the same seven source files, zero APIs and the original graph revision.
Cold/warm measurements were 3.51/4.35 seconds, compared with the earlier profiled
62.82/62.58 seconds. [The live project's samples](live-profile-02.json) retained
four API registrations and measured 2.73/1.07 seconds. These Windows samples ran
under concurrent work and are not latency guarantees.

The inventory lists encountered pruned prefixes and reasons. It does not count
or claim to inspect their descendants. Directory-presence diagnostics do not
change source/build identity when observation creates its own outputs.

Actual Chrome [API replay checks](../browser-patch-scope-api.json) and the
[source-quality gate](../source-quality-patch-scope.json) passed after integration.
Managed-example and whole-repository acceptance are recorded separately.

The [adoption fixture](../trial-audit/source-scope-adoption/README.md) also
preserves a short scripted kickoff and 11 executed checks: ignored first-party
modules, manual review tests, dependency/output pruning before descent, new
top-level source, and rejected out-of-scope execution bindings. It is separate
from the full application's real dialogue and runtime acceptance.

## Retained failures

- New tests first reproduced missing pruning, foreign API discovery and missing
  out-of-scope binding rejection: [initial regression receipt](initial-regressions.json).
- Existing CodeGraph tests caught observer-cache creation changing diagnostic
  scope and a previously returned snapshot. The repair separates diagnostics
  from semantic cache identity: [integration review](../publication/source-scope-integration.md).
- The first live-project measurement script incorrectly assumed every
  `scandir` call belonged to the project. A validator legitimately loads its own
  packaged JSON schemas. The corrected script counts those resource reads
  separately: [failed measurement](../source-scope-live-profile-01.json).
- A standalone engineering-tree fixture declared only `web` while keeping an
  unrelated executable binding outside that scope. Only that fixture's worker
  source/binding moved into `web`; all original alias/scope assertions remain.
  [Failure and repair evidence](integration-failures.json) records the migration;
  the out-of-scope guard stays strict.
- The first two isolated Git exports rejected the examples' approvals because
  local CRLF `.gitignore` bytes differed from their LF Git blobs. All other
  current model, managed and watched files matched. Both examples now use their
  existing LF convention and passed a separate complete native candidate,
  retaining the original approvals and strict raw-byte checks. The
  [third isolated export](../clean-staged-export-patch-03.json) passed with
  [682 current inputs matching Git](../example-source-scope-portable-staged-parity.json).
  See [the byte comparison](../clean-export-source-scope-diagnosis.json).
