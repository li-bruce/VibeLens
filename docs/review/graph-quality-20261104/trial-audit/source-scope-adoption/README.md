# Source-scope adoption trial

Status: PASS within the stated evidence boundary.
Evidence class: a scripted Chinese kickoff exchange plus an executed isolated fixture. This is not independent human feedback, a new application implementation, or a completed application acceptance run.

## Instruction adoption

The trial reads the maintained `skills/vibelens/SKILL.md`, `references/source-scope.md`, and `references/requirements-dialogue.md`.

`dialogue.zh-CN.md` preserves the supplied user sentence exactly. A1 classifies the planned source, dependencies, and artifacts before any scan. It keeps `modules/private-core/` as owned source despite its `.gitignore` entry, retains `review/manual-tests/`, and prunes the exact upload/runtime subtrees. U2 confirms directory ownership. No ownership clarification is repeated for the supplied paths. The sole main-dialogue question is the Skill's required drive/observe choice; U3 is explicitly simulated. No business behavior or architecture is added.

The fixture writes the same `sync-planned.json` configuration to its isolated `sync.json` before invoking canonical inventory. The independent project root remains `.`. An extra ambiguous `vendor/plugins` counterexample is kept separate from the user's confirmed scenario: unclassified code stays visible, ownership remains pending, and the scanner does not invent an answer.

## Executed evidence

Run from the maintained repository root:

```powershell
& 'docs/review/graph-quality-20261104/trial-audit/source-scope-adoption/commands.ps1'
```

The exact Python command is preserved in `commands.ps1`; `run.log` preserves stdout/stderr. Exit code: 0. All 11 fixture assertions passed. The environment emitted `Failed to find real location of C:\Users\Lvi_P\miniforge3\python.exe`; execution continued successfully, including the child test. The console's non-ASCII path rendering differs from the UTF-8 path in `results.json`; the structured result is authoritative for the fixture location.

| Check | Actual result |
| --- | --- |
| Ignored first-party module | `modules/private-core/service.py` inventoried and `private_identity` indexed |
| Pruned storage | Instrumented `os.scandir` visited none of `node_modules/`, `.venv/`, `data/uploads/`, `review/runtime/` or their descendants |
| Review code | `review/manual-tests/test_app.py` inventoried, AST-indexed, and one synthetic application test executed successfully |
| Later top-level source | `later_feature/new_handler.py` independently discovered and reported as an unregistered-source obligation |
| `.gitignore` advice | Editing it changed the hashed scope input while preserving discovered source |
| Out-of-scope executable anchors | Four dependency/artifact bindings rejected by canonical validation |
| Narrow roots | Standalone inventory allowed; full-project stategraph coverage claim rejected |
| Ambiguous ownership | `vendor/plugins/candidate.py` retained; no dependency ownership inferred from its directory name |
| Unsupported scope category | `unknown` category rejected |
| Unsupported source adapter | Go file discovered with an explicit incomplete-mapping error |

`results.json` contains the complete initial inventory, visited directories, canonical input hashes, exact rejection/error messages, and the child test argv/cwd/stdout/stderr. It never counts unvisited descendants as inspected. Scratch is retained under `.validation/source-scope-adoption-20261104-3muunwa2`.

## Limits

Directory ownership is a declared decision. Canonical scope validation cannot prove that a syntactically valid dependency/artifact classification is semantically correct. The dialogue must preserve the user's first-party declaration and ask only when ownership is genuinely unclear. Source discovery and successful parsing do not establish business completeness, mapping acceptance, or runtime monitoring correctness.

This task writes only this review folder and its isolated `.validation` scratch. It changes no product, Skill, or example source and performs no commit or push.
