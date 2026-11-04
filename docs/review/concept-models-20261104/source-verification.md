# Source, API and data identity verification

This review resumed the interrupted implementation on `feat/concept-model-contracts`.
The checks below ran against the maintained Skill source, before managed example
copies were refreshed. No production application or external database was changed.

## Verified behavior

- A source declaration has one identity derived from its relative file path and
  qualified symbol. Business operations and contextual appearances retain their
  own identities and explicitly reference that declaration.
- Formal parameters remain distinct from captured return fields and state enum
  values. A registered state-parameter representation can reference the exact
  source parameter without equating every state value with it.
- Independent API registrations remain distinct even when they use the same
  handler, method and route. Moving statements to other lines preserves their
  identities. Ambiguous legacy endpoint identities produce an explicit split
  record instead of silently moving a user's selection to one endpoint.
- Data operations identify reads, writes, transactions and transformations
  separately. Existing query-wrapper records remain readable. Runtime target
  provenance and target-access checks apply to every operation role.
- Lexical ancestors provide source structure without adding an unrelated
  documentation obligation. Explicitly mapped declarations and the existing
  all-symbols documentation checks retain their requirements.

## Results

| Command or suite | Result |
| --- | --- |
| `tests/test_layer_source_identity.py` | 14 passed after core-isolation follow-up |
| `tests/test_api*.py` | 20 passed |
| `tests/test_code_graph.py` | 31 passed |
| `tests/test_source*.py` | 57 passed on the completed run |
| `tests/test_database*.py` | 105 passed |
| `tests/test_lifecycle_definitions.py` | 4 passed |
| `tests/test_protocol_reuse.py` | 3 passed |
| `tests/test_policy*.py` after projector composition fix | 27 passed |
| `tools/test_multilanguage.py` | 28 passed |
| Black, 14 changed source/test files | No changes required |
| Ruff, 13 maintained source files | Passed |

The combined Python regression count above is **289**. The initial suite had 12
identity tests; composition and core-isolation regressions bring it to 14. Database tests here use
their repository fixtures; this report does not claim a live database acceptance.

## Composition failure found in the independent trial

The first native file-sharing model applied the shared-policy projection before
source enrichment. Exact validation rejected it with `maps relation is outside
the exact policy projection`: physical source decoration had changed a
policy-owned node, and optional AST nodes could change its chosen implementation
anchor on the next projection.

The source projector now connects an exact policy node to its canonical physical
declaration without changing that node's payload. Policy inference excludes
optional AST/index declarations when selecting an implicit implementation anchor;
an explicit implementation node still applies. The new regression checks both
projection orders and repeated fixed points. A forged policy field is still
rejected. No policy-validator check was relaxed.

## Failure and retest

The first source-suite run finished with 53 passes and 4 errors. Each error came
from creating a temporary Windows junction (`mklink /J`) in `.validation`;
the operating system returned `Access is denied`. An isolated junction attempt
confirmed the same environment restriction. The same unchanged suite then ran
with the tool's approved permission escalation and passed all 57 tests. No test
was skipped, weakened or converted to a mock.

## Limits

Static syntax establishes declarations and supported registration/call links.
It does not establish that a call actually ran, or resolve arbitrary reflection
and dynamic dispatch. Runtime evidence remains a separate input. These tests do
not replace the complete concept-contract, browser or recording acceptance.

## Focused capture follow-up

The real trial's focused recording exposed a separate adapter defect: a filtered
read returned no evidence ID, but its snapshot was still submitted. Both Python
and JavaScript probes now omit that snapshot. Real capture failures remain in
producer health, and a forged non-null ID still reaches strict collector rejection.
The three `tests/test_snapshot_scope.py` regressions pass. The existing 28-test
multilanguage suite was rerun unchanged and also passes. These add three distinct
tests to the earlier 289, for **292** across this report's suites; the actual HTTP
failure/retest and local initialization repair are documented in `trial/README.md`.
