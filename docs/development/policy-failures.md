# Failure and repair record

## First policy regression run

Command: `python -B tests/test_policy_network.py`

Result: 11 tests, 2 errors.

1. The policy group used an empty summary. The existing graph validator rejected it with `node lacks developer explanation`. Fixed the generated group, retaining the existing validator requirement.
2. Windows sandbox denied a write inside the process default temporary directory. Moved test fixtures under the worktree's ignored `.validation/policy-network/` directory.

Retest: all 15 policy tests pass after the subsequent integration additions.

## First broad unittest-discovery run

Result: 208 tests, 3 failures and 3 errors. The worktree did not yet have the pinned JavaScript parser/formatter dependencies; Windows subprocesses also decoded UTF-8 as GBK. Importing every test in one Python process exposed an existing `bo_stategraph` module/package collision before the whitebox test.

Repair: install both pinned npm lockfiles in the isolated worktree, use `PYTHONUTF8=1` / `-X utf8`, and use the repository's isolated-process test runner. No test assertions were removed. Individual code-graph (22), source-quality (5), requirements-dialogue (22), whitebox (8), policy (15), and stategraph-module (11) runs pass.

## Tooling validation

`quick_validate.py` initially could not import its PyYAML dependency. This is a validation-tool dependency, not an application runtime requirement. Installed the dependency in the local development environment; validation passes. Sandbox temporary writes were redirected to the workspace.

## Whole-repository checks

The release runner initially stopped at the clarification fixture because unused policy-core files had been copied into projects without a policy declaration. The upgrade now installs the independent core only when configured (or explicitly requested). Managed library recognition requires the exact allowed path, the recorded hash and the checker's own canonical bytes; a forged local manifest cannot hide edited application source.

Further runs correctly rejected changed managed copies whose ownership fingerprints were old. Reviewed the canonical changes, synchronized copies, and regenerated the ownership records with a stated reason. The clarification regression passed all 13 steps. No protected assertions or capture requirements were removed.

The first reviewed example verification lacked the launcher's `scratch` directory and overlapped a framework edit. Its missing-directory and changed-candidate failures are retained. The directory is now created before verification, and source is held stable during acceptance. The delivery example then passed inspect, verify, accept and check.

The next release run passed the earlier gates and stopped at the existing multi-language fixture: this fresh worktree lacked its pinned `jsdom` dependency. Installed `examples/multilanguage/package-lock.json` with `npm ci`; the unchanged fixture then passed both modes and all 18 actual Python/JavaScript/React/Vue cases.

## Standalone evidence freshness

Source review found that `bo_policy check --evaluation` checked declarations and signatures but did not compare the report's source fingerprints with current file bytes. The full coding gate already did. The standalone command now applies the same source-freshness check. A new regression first accepts current evidence, changes the actual predicate, and requires rejection of the old report. All 23 policy tests pass.

Original command outputs and subsequent release results are indexed under [shared-policy review](../review/shared-policy/README.md). Framework changes during the independent trial are recorded separately from business development costs.

## Native project integration gap discovered after the first complete run

The isolated diagnosis setup used the canonical `change_sync begin` directly, without the trial's project-side compatibility hook. The committed `088514b` failed: `project.schema.json` embedded an old copy of the model schema and rejected `maps`. The trial had documented a local hook for this enum and for policy/data element-order oscillation; its adapted acceptance did not establish native framework support. The first complete repository suite had not exercised this combination.

Added two targeted regressions and ran them against a clean export of `088514b`: native project validation failed, and alternating the actual policy/database projectors changed the model. The original red run is preserved. The project envelope now references the canonical model schema, registered offline by the protocol validator. Its previous constraints are retained; exact policy projection, orphaned elements and forged mapping edges are checked semantically. Policy projection now preserves existing node/edge order, as the database projector already did.

The updated 27-test suite passes, including validation from an unmodified installed runtime and actual unknown/error capture through BOProbe and evidence verification. The actual assisted V2 project also passes direct canonical validation without importing its hook. Its independent compatibility regression removed the hook and CLI wrapper, retained the native journal adapter, and passed 16 application tests, 84 business assertions, 10 evidence checks and actual browser recording/replay. That work is recorded separately from the earlier adapted V2 and its costs. Both installed repository examples completed a normal new inspect/verify/accept/check change; no prior approval was regenerated. The Skill now distinguishes project-native adapters from hooks that replace canonical validation/projection and requires the latter gap to remain explicit.
