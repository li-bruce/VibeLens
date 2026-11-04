# Existing live trial: managed observer upgrade

The old file-sharing trial was upgraded through canonical `bo_upgrade.plan` and
`bo_upgrade.apply`, using `observer_runtime` and its actual served viewer folder
`static/graph`. There is no `integrations/bo_viewer` target in this project.

The plan changed 39 managed observer/viewer files, with no conflicts or retired
files. No native state/execution-core files appeared in the change list. Frozen
hashes cover 2,029 project files: application source, declarations, verification
inputs, prior review evidence, personal configuration, recordings and data.
`protected-verification.json` confirms all of them were identical immediately
after the managed copy.

The old process 65916 was verified by its two listener ports, launcher identity,
observer project ID and current source binding. It stopped through its own
`runtime/stop.json` mechanism. The unchanged application was restarted with an
absolute `dev.py` path and a hidden process window. The current listener process
is 56364, on the original addresses:

- Application: `http://127.0.0.1:50957`
- Graph: `http://127.0.0.1:50958/graph?lang=zh-CN`

Read-only observer checks returned HTTP 200, the same project/build identity and
`binding.status: current`. API projection returns four literal registrations;
all five original HTTP capture anchors retain their IDs and exact selectors.
No application HTTP requests or business scenarios were executed in this upgrade.

`served-assets.json` verifies six served geometry, API-name, clustering and viewer
assets against canonical source hashes. `web-verification.json` records the live
project/build identity and endpoint metadata.

After startup, the read-only source query refreshed `.stategraph/code-graph.json`.
The SQLite file hash also changed because native initialization incremented its
two file-header counters once. `verify_restart.py` proves this by replacing only
bytes 24–27 and 92–95 in memory: the reconstructed hash exactly matches the frozen
database hash, so every other database byte is identical. It never writes those
bytes back to the database. `restart-hash-check.json` records no other protected
file changes; application rows, recordings, personal configuration and prior
evidence remain preserved.

This is an observer-only upgrade and read-only availability check. It does not
replace or regenerate the trial's previously accepted business evidence.

The final label-containment correction was applied in a second managed plan.
Only `static/graph/containment-geometry.js` and `static/graph/layout.js` changed.
The same process kept serving both ports; no application restart was needed.
All 2,029 protected files stayed byte-identical during this second copy, and
`served-assets-final.json` confirms both final files match canonical hashes with
the observer binding still current. The `*-final.json` records preserve this
second pass separately from the initial upgrade evidence.

An additional browser-discovered camera/layer-fit correction changed only
`static/graph/spatial-renderer.js`. The `*-fit-fix.json` records preserve this
third static-only phase. Its served hash matches canonical source, process 56364
was not restarted, and all 2,029 protected files stayed unchanged.

After the full multilingual regression check, the final `adapter-compat` phase
copied the corrected parser script plus `spatial-labels.js` and the latest
`spatial-renderer.js`. The parser retains syntactic callback entrypoints without
inventing HTTP endpoints. Both served caption assets and the installed parser
match canonical hashes; the unchanged process still reports a current binding,
four literal endpoints and no source-parser errors. Its separate phase records
again show all 2,029 protected files unchanged during the managed copy.

The `api-observation` phase installs the final exact HTTP observation correction:
nine managed Python files and fourteen viewer files, including `api-observation.js`.
The verified process 56364 stopped through its native stop file, and the unchanged
launcher restarted in a hidden window on its original ports as process 95532.
The live `/api/view` snapshot contains four physical endpoints, five original
qualified capture addresses and five explicit mapping edges. There are no API
mapping issues or parser errors, and the original source binding remains current.

`final-verification-api-observation.json` checks every changed installed file and
every changed served viewer asset against canonical hashes. All 2,029 protected
files remained identical during copying. After the necessary Python restart, only
the database's two file-header counters changed once; reversing those bytes in
memory reproduces the frozen database hash exactly. Business source, state-machine
definitions, data rows, personal configuration, prior histories and evidence are
preserved. Observer-only reads performed these checks; no business requests ran.
The strict check is also run through the newly installed observer entrypoint and
saved separately as `installed-api-check-api-observation.json`.

The final `legacy-focus` phase updates only `static/graph/graph-links.js` through
the managed upgrader. Its canonical, installed and served hashes agree; process
95532 continues on both original ports without a restart. All 2,029 protected
files remain unchanged during this copy, the source binding stays current, and
the four-endpoint/five-capture API snapshot is preserved. Separate phase receipts
record the plan, copy and read-only verification.
