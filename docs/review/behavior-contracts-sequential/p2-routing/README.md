# P2 guided construction and routed review

Branch: `feat/behavior-contracts-sequential`, after P1 commit `fa1baa54`.
Status: P2 implementation and regression complete. No independent chat trial was
started. P3–P7 retain their own implementation and acceptance obligations.

The final full runner passed 944 Python unittest executions across 79 suites,
plus JavaScript, integration, HTTP, installation and package checks. Both examples
passed verification, acceptance and freshness checks, then passed from a clean
staged Git export using frozen approvals. Source lint/format checks passed for
212 Python and 138 JavaScript modules. Eight supplemental ledger tests cover the
final engineering-only receipt check described below; runtime sources and frozen
exports are unchanged by that repair. Counts describe executions, not unique
features or dialogue acceptance. See [results.json](results.json).

## Implemented responsibilities

- Construction gaps follow canonical scope and retain unrelated future work.
  Target placement cycles fail before scheduling. Obligations remain independent
  of authored questions; changing/removing them requires source-backed history.
- Decisions retain one store, with strict V3 routing, explicit authority, stages,
  evidence requirements, conditional branches and immutable partial replies.
- Optional depth/language preferences change wording only. Human rounds contain
  up to three ready questions; agent/checker work is separate. Old formats retain
  their original checks and cannot use unvalidated routing to skip questions.
- `bo_concepts review` derives a model index and one shared focus projection.
  The diagram, shown/omitted identities and semantic snapshot match. Generating
  it records neither presentation nor confirmation. Web remains a viewer.
- Skill guidance now follows inventory → candidate models → gaps → routed work
  → focused review → confirmation. Existing state/rule validation and subsequent
  native binding/observation authority are unchanged.

## Failure, repair and retest

| Record | Finding | Repair / retest |
|---|---|---|
| `scope-before.log` | New fixture initially used `mode` instead of the existing applicability `status` field; target cycle was also accepted | Corrected the fixture without changing the native validator |
| `scope-reproduction.log` | Unrelated construction gaps blocked a confirmed increment; a later target question still blocked it; cyclic target placement was accepted | Shared scoped construction selection and strict cycle rejection; `scope-after.log` |
| `construction-compatibility.log` | Initial routing hid legacy-format V3 questions while requesting classification | Keep the original question available and add agent classification work; `construction-compatibility-retest.log` |
| `review-first.log` | The Windows sandbox denied a default temporary directory | Used the existing workspace-local TEMP/TMP fixture setup; `review-retest.log` |
| `package-first.log` | Managed examples had not yet received the new maintained runtime | Regenerate through `tools/sync_runtime.py`; do not edit installed copies |
| `legacy-bypass-before.log` | V2 decisions could borrow unvalidated V3 stage metadata to skip a blocking question | Restrict routing semantics to strictly checked V3; `legacy-bypass-retest.log` |
| `locale-before.log`, `locale-regression-before.log` | Explicit Chinese review still showed the English question | Shared wording projection now honors the review locale without changing decision IDs, preference or semantics; `locale-retest.log` |
| `full-verify.log` | The release runner refused examples whose review had changed since their prior accepted verification | Preserve that guard; explicitly verify/accept/check the reviewed current candidate before rerunning release checks |
| `plan-retest.log` | Once A01 had partial evidence, changing its status to passed escaped the old evidence-presence check | Require an explicit executed result for that case; partial/other-case receipts cannot promote it. Eight tests pass in `plan-retest-fixed.log` |

The new suite includes product/technical/mixed wording, skipped preference, role
changes without authority changes, scope-limited work, five human questions plus
agent/checker work, conditional choices, free-text ambiguity, partial replies,
contradictions, restart, source evidence versus human guesses, history protection,
source-free targets, missing typed relations and real CLI preview export.

These are synthetic service/CLI regression tests. They do not authenticate prose,
infer every unstated intention, execute referenced runtime evidence or constitute
the fresh independent dialogues reserved for P7. Later stages verify the source,
runtime, evidence invalidation and actual usage of these records.
