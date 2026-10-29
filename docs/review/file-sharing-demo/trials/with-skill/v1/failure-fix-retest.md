# Development failures, fixes, and retests

These records describe actual development runs. No defective business behavior was deliberately planted. Evidence omission and malformed protocol inputs are isolated checker tests; transport fault and bounded-queue cases test observer isolation.

| Finding | Fix | Evidence |
| --- | --- | --- |
| Initial design record used unsupported enum values and a wrong question-history shape. | Corrected records to the actual Skill contract. | design-preparation-checks.json; discovery-validation.json |
| Windows sandbox temporary directories blocked test databases and dependency installation. | Used project-local test directories and the project virtual environment. | unit-tests-attempt-02.json; later test receipts |
| SQLite context managers did not close independent test-reader connections. | Explicitly closed the readers. | unit-tests-attempt-02.json; unit-tests-attempt-03.json |
| The branch project schema omitted its supported policy maps edge. | Project-only additive enum compatibility with unchanged exact projection validation. | database-sync-attempt-02.json; integrations/bo_schema_compat.py; evidence-checks.json |
| Policy/source projection ordering caused false stale-graph results. | Retained existing order while preserving every identity, type and dependency. | history/pre-final-change-inspect.json; final change-check.json |
| Data result summaries and SQL shape capture were incomplete. | Captured selected results through the native runtime result envelope and supplied parseable query shapes. | history/pre-final-change-verify.json; final runtime-observations.json |
| The generic inventory needed explicit cases for policy-node fields and a safe password-presence projection. | Added actual policy cases and captured only password presence. | final implementation and whitebox checks |
| A metadata collector accepted an additive column, so a test incorrectly expected a constraint violation. | Checked the real catalog change instead; no claim that extra columns violate the declared schema. | evidence-checks.json |
| A headless exact-text locator included a child caption. | Retained the expected owner and matched the actual owner cell. | browser/attempt-01-failure.json |
| Windows virtual-environment descendants left an old graph listener running. | Terminated only the owned process tree, checked listeners, and added tree cleanup to the launcher. | running-services.json; final served-build checks |
| Design and runtime preference owners differed. | Added an explicit layout alias and preserved original preference records. | preferences-before-migration.json; browser/replay-diagnostics.json; final browser report |
| Canonical framework projection source changed during acceptance. | Performed a second normal framework upgrade and revalidated; kept the immutable baseline. | framework-upgrade-02.json; framework-parity.json |

Business, mapping, state, project checks, and browser acceptance are reported separately in final-review.md. Simulated answers are retained verbatim and are not independent human testing.
