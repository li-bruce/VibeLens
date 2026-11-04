# VibeLens v0.12.0 release review

Release candidate: v0.12.0, prepared on 2026-11-04 and checked on 2026-11-05.
The independent conversation trial follows the published tag; it is not included
in the pre-release results below.

Scope: the concept-first implementation plus the five reproducible defects in
the [follow-up audit](../../assessment/2026-11-04-implementation-audit/README.md).
The [original implementation evidence](../concept-models-20261104/README.md) is
retained separately.

Required release checks: targeted negative regressions, maintained-source quality,
managed-copy parity, original complete verification, accepted conceptual browser
workflow and clean Git export. The new isolated conversation must install the
released Skill, preserve its dialogue and report design, mapping, execution,
business and viewer results separately.

Simulated user answers are labelled as simulated in the review. They provide
repeatable workflow evidence, not a human usability study.
The separate [conversation trial plan](trial-plan.md) defines the next test's
coverage; it remains a plan until actual dialogue and result evidence are added.

## Repairs from the follow-up audit

| Audit item | Implementation | Regression boundary |
| --- | --- | --- |
| F1: rule attached to the wrong business action | Exact native applicability targets and observed invocation ownership | Reject wrong/extra targets and unrelated recorded decisions |
| F2: effect declaration without execution/completion evidence | Mandatory transition-effect bindings, typed completion and independent expected outcome | Actual SQLite commit, independent SELECT, incorrect transaction identity and shared effect functions |
| F3: opposite conditions drawn identically | Preserve relation semantics and polarity in labels and grouping | Explained English/Chinese labels and semantic grouping are covered; direct source-mode guard inspection is in the new conversation plan |
| F4: conceptual state hierarchy disappears | Separate display containment adapter | 2D/3D regions, region-off fallback and ambiguous ancestry |
| F5: Functions view loses relations | Include static call, parameter and mapping relations | Preset completeness and explicit user filters |
| W1-W3: maintenance and preview gaps | Concept report in recall, localized preview, stable boundary glyph reuse and automated accepted-browser runner | Scoped recall, UTF-8 export and source-free design previews |

Original audit failures remain in their own report. New evidence in `checks/`
records this release's repairs; historical approvals are not rewritten.

## Release checks

| Check | Recorded result |
| --- | --- |
| Original complete suite, including database adapters | [Passed](checks/full-verification.json), 459.06 seconds; original checks remain enabled |
| Maintained source syntax, lint and formatting | [Passed](checks/source-quality-release.json) |
| Actual PostgreSQL, MongoDB, Redis and Neo4j via Python and Node | [Passed](checks/databases-live.json) |
| Accepted application and browser interaction | [Passed](checks/concept-browser/README.md): five verification categories and seven browser groups |
| Managed runtime/viewer copies and both shipped examples | Passed in the complete suite after migration from preserved baselines |
| Fresh Skill ZIP extraction and all 349 file hashes | [Passed](manifest.json) |
| Clean Git export using only frozen approvals | [Passed](checks/clean-export.json); neither example was regenerated or reapproved inside the export |

The accepted example candidates are
`1c6adf08e2f6c33fa73849ed7815362ad02108052689e8f9a1f17e5828709db4`
(delivery) and
`9ab37d2b3eb706a680fd6dcf2a22dd2215f8fa4a6979254b0a4884dd609f303e`
(team archive). Their current acceptance is frozen under each example's
`.release/stategraph/release-v0.12.0` directory.

The browser's final graph overview is saved at 13% zoom when Timeline is open.
Lifecycle duration and selected values are readable, while graph captions at
that scale are too small for detailed inspection. This is a functional acceptance,
not a claim that every saved view is visually polished.

## Retained preparation failures

- Team-archive's first baseline command lacked the installed JavaScript parser
  path. It stopped before creating a baseline. The configured retry succeeded.
- The first migration helper assumed inspection writes `candidate.json`. The
  public inspection returned a valid candidate ID but writes diagnostics instead.
  The helper now uses the existing snapshot API to compare protected content.
  The original baseline is unchanged.
- The first conceptual browser preparation overlapped active source edits and
  correctly rejected its changing candidate. A later attempt passed acceptance
  but could not locate Chromium in the sandbox's cache. Installed Chrome is used
  for the subsequent browser run; neither attempt counts as a UI pass.
- A final review reproduced a false rejection when two transitions reuse the
  same effect function. The correction selects each invocation by its actual
  transition owner. A second regression covers equal local call IDs in different
  entity/attempt scopes, following the existing lifecycle identity contract.
- An isolated browser preparation exceeded its existing 180-second observation
  command limit while example migrations also ran. The timeout is retained;
  final heavy checks run serially with the original limit.
- Packaging identified CRLF in two new maintained Python modules. Their bytes
  are normalized to LF before final acceptance so Git exports, installed copies
  and reviewed tool hashes agree. The earlier browser pass remains identified
  as pre-normalization evidence.
- A later serial observation run also timed out, disproving contention as the
  sole explanation. Profiling found repeated full-path resolution in conceptual
  freshness checks. The secure source reader now handles each check directly,
  retaining byte reads and current ancestor/link checks. One actual 190-event
  roundtrip measured 19.79 seconds initially and 4.88 seconds after the change;
  this is a local case measurement. Same-size/restored-timestamp changes,
  unreadable configuration and outside-junction substitution have regressions.

## Boundaries

The v2 concept binding currently supports one primary native state model and
Boolean policy results. Existing native engine limits still apply. Maintenance
requires the coding agent or host to invoke the prescribed workflow. Independent
finite cases check implementation and observed behavior; they do not establish
all possible executions or natural-language understanding.
