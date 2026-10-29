# Native-framework compatibility regression

The project now uses the candidate framework's own schema validation and stable policy/data projection, without the former schema/projection shim or its CLI wrapper. The actual V2 graph passes both the canonical source interface and the installed interface in independent processes. The project-native flat-state journal view adapter remains byte-identical. This is a compatibility regression, with no added business behavior and no change to V2 business iteration costs.

Framework status: **unreleased working-tree candidate**. The normal upgrade updated five managed files with no conflicts. The post-upgrade plan reports no remaining changes or conflicts. Repository-wide release acceptance is outside this result.

Native accepted build: `206520c81b9f2adc70268f88ac3dd39867566f217d628062851c72591abe35bf`. Candidate: `19d36de8a1332bd8328ff8408cf0c5d39441a38b86d9961f29d645e27c1e246b`.

Previously adapted V2 build: `9de5ee5b1e2eab3f88dff8743e9544bc439900d4b44e82efb9b720e453b0b025`. That result used the removed schema/projection shim. Its exact source and acceptance evidence remain in `previous-adapted/` and the original `../iteration-02-revoke/` directory. This native pass supersedes its framework compatibility status; it does not retroactively turn the adapted result into a native result.

## Verification

- Implementation mapping, state constraints, business rules, and project checks passed separately.
- 16 unchanged application tests, 84 business assertions across two scenarios and on/off/fault observation modes, and 10 existing evidence checks passed.
- Original probe fields, cases, whitebox expectations, mapping requirements, source inventory exclusions, and independent business assertions remain protected.
- Native projection is idempotent. The machine, policy, feature inventory, node/edge IDs, and order match V2. 176 protected files, including V2 costs and evidence, are unchanged.
- Headless browser regression passed 11 original workflow steps and 12 revocation steps, with 12 screenshots and no graph console/page errors. An already-open, previously successful recipient download link returned HTTP 403 after the owner's revocation committed; the owner downloaded identical bytes afterward. Both actual recordings were stopped and replayed; the revoke state path is private -> shared -> private. Obsolete-version recordings are hidden from the current list.
- Architecture and post-browser current-source checks passed. Personal positions, notes, filters, expansion, and spatial settings were preserved.

## Evidence and costs

`native-canonical-*-project-check.json` and `native-installed-*-project-check.json` identify the real interfaces and confirm no shim was loaded. `upgrade-plan.json`, `upgrade-apply.json`, and `post-upgrade-plan.json` retain the normal upgrade evidence. `source-diff.json` distinguishes framework-copy changes from shim removal and verification wiring.

`verification/`, the copied gate receipts, `runtime-observations.json`, and `evidence-checks.json` retain formal and independent runtime evidence. Screenshots, downloaded bytes, raw recordings, and steps are in `browser-regression/` and `browser-revocation/`. The current source is frozen in `native-source/source.zip` with individual file hashes. The instruction is preserved verbatim in `request-original.txt`.

`development-costs.json` records this separate regression's upgrade, repeated checks, browser runs, and failures/fixes. The first new-canonical begin rejected the pre-upgrade installed snapshot; the exact prior accepted baseline was then established through the previous installed interface before upgrading. No baseline was reset. A local archive-label variable was corrected and the full gate repeated. Neither item is charged to the frozen V2 business cost record.

## Run and boundary

Application: http://127.0.0.1:8850/ . Graph: http://127.0.0.1:8847/graph . Use `.venv/Scripts/python.exe -B run.py` from this project to start both services. The existing demo accounts and password are unchanged.

Reproduce with the project environment: `python -B tooling/verify.py`, then `python -B tooling/browser_check.py --out review/framework-compat-01/browser-regression`, then `python -B tooling/browser_revoke_check.py --out review/framework-compat-01/browser-revocation`. Start from a fresh current-build process when repeating the full browser sequence.

Current failures: none. This is local scripted AI acceptance of the project's framework compatibility, not production, independent human, or upstream release acceptance. Existing observer fault modes and isolated negative evidence checks were retained; no new business defect was planted. No further feature, fault-injection stage, or product-material export was started. Work stops after this regression.
