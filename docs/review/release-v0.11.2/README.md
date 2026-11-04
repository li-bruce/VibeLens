# v0.11.2 source-boundary patch review

Status: the [local candidate gate](candidate-gate.json) passed, including the full
host repository checks, package, native examples and isolated Git export.
Remote v0.11.2 CI, publication and installation have separate release checks.

The [isolated reproduction](../graph-quality-20261104/trial-audit/scope-reserved-assessment/README.md)
found an actual scope inconsistency: source/API analysis admitted Python modules
under `bo_stategraph/config` and `bo_stategraph/data`, while the project tree
unconditionally hid those paths. Missing file owners caused graph construction
to raise `KeyError`, including the mandatory API snapshot path.

The repair puts the default observer-storage boundaries in the shared policy.
Explicit, narrow owned-source overrides must restore AST/API analysis, physical
bindings and file-tree ownership together. Default personal preferences and
recordings remain excluded; hash-only watched inputs retain integrity checks.
Existing independent root discovery, mapping gates and native state engines stay
required. The six protected state/contract files retain their original hashes.

The frozen package contains 305 Skill files:

- Skill Git tree: `82b7f501697334bb83a82b5863ac7c068785b6bf`
- ZIP SHA-256: `4fc87cc1f9ab08fcaf69f64cdbf1e4bc2c73f882e0ab9c9ff85f2e501a402607`
- [Package manifest](manifest.json), including fresh extraction and staged-blob hashes

## Current evidence

The [focused regressions](../graph-quality-20261104/trial-audit/scope-reserved-assessment/fix-regressions.json)
passed 25 source-scope, 31 code-graph, 20 API and 18 source-documentation tests.
They cover both reserved paths, default output exclusion, explicit owned-source
overrides, physical bindings and file-owner consistency. The existing root
discovery, soft-exclusion and watched-input checks remain required.

[Source quality](../graph-quality-20261104/source-quality-0112.json) and
[package-copy checks](../graph-quality-20261104/package-copies-0112.json) passed.
The [delivery](../graph-quality-20261104/examples-delivery-reserved-boundaries-0112-final-acceptance-summary.json)
and [team-archive](../graph-quality-20261104/examples-team-archive-reserved-boundaries-0112-final-acceptance-summary.json)
examples completed their native generate, seal, scan, inspect, verify, accept and
current-check workflows. Their frozen candidate identities match the
[682-input staged parity check](../graph-quality-20261104/example-reserved-boundaries-0112-staged-parity-02.json).
The [isolated Git export](../graph-quality-20261104/clean-staged-export-reserved-boundaries-0112-report.json)
then passed both native checks without regenerating or reapproving them.

[check_candidate.py](check_candidate.py) verified the current host full gate,
these exact receipts, the staged Skill tree, every ZIP entry, the protected cores
and unchanged example subtrees from that clean export. The aggregate records each
receipt's digest and retains the failure evidence. Remote v0.11.2 CI,
publication and installation need separate receipts.

## Retained failures and earlier checks

The [full sandbox run](../graph-quality-20261104/full-verification-09-reserved-scope.json)
failed the existing Windows junction setup permissions. Its result is retained;
the unchanged [full host checks](../graph-quality-20261104/full-verification-10-reserved-scope-host.json)
then passed with database verification enabled. The environment failure was not
replaced or counted as a pass.

The original reserved-path exceptions remain in the
[isolated assessment](../graph-quality-20261104/trial-audit/scope-reserved-assessment/README.md).
The [earlier geometry](../graph-quality-20261104/browser-patch-geometry.json) and
[large source-tree profiles](../graph-quality-20261104/source-scope/README.md)
remain historical evidence. They are not fresh measurements of this Python patch.
Viewer assets are unchanged from the
[official v0.11.1 tag's eight passing CI jobs](../graph-quality-20261104/publication/ci-tag-7cc0bce9-final.json);
the aggregate checks that exact viewer subtree before reusing its frontend proof.

The preceding [v0.11.1 release](../release-v0.11.1/README.md) remains immutable.
Its official tag CI passed all eight jobs. A later main rerun exposed a separate
test micro-zoom error; its original failure and the time-based staged-zoom repair
are retained in the [browser receipt](../graph-quality-20261104/publication/lifecycle-main-staged-zoom-repair.json).
The passing local aggregate does not replace this release's remote CI or tagged
installation checks.
