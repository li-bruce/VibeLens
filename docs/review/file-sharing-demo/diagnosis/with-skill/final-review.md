# Controlled stale-page diagnosis

The supplied controlled fault is repaired in this isolated copy. The revocation DELETE compared the recipient column to the acting owner (`linzhou`) rather than the selected recipient (`xuning`). It therefore deleted zero rows, left the grant present, and the existing per-request read policy correctly continued to permit that recipient. The domain fix changes one expression in `app/service.py:141` from `actor` to `recipient_id`. It matches the pre-fault source baseline. No file, policy, state rule, observer, independent assertion, or test was weakened to obtain a pass.

This was an explicitly supplied controlled-fault test after `.stategraph/diagnosis-03` began, not a naturally discovered production defect. The original delivery and other trials/chats were not used for investigation. All source edits, services, synthetic data, and artifacts belong to this copy. Only the permitted original virtual-environment executable and selected Skill interfaces were used. Ports are 8852 and 8853.

## What the graph actually contributed

1. The state network and native witnesses showed private -> shared -> shared, with `has_recipients=true`, after the failed revoke. The state accurately reflected the surviving relationship; changing the state declaration would have hidden the real problem.
2. The rule network showed owner authority for revoke and, later, `is_owner=false`, `received_share=true`, and `read_allowed=true` for xuning. This explained the actual decision from current facts. It did not prove that revocation achieved its intended effect.
3. The data node `db_delete_share` returned rows=0; the revoke commit recorded `removed=false` and `grant_count=1`. An independent SQLite query confirmed the xuning grant remained. Native source/impact inspection connected the changed revoke function to its deletion, transaction, state update, and neighboring access behavior.
4. The recorded request field `recipient_id=xuning` did **not** establish the actual compiled SQL binding. Source inspection found `shares.recipient_id == actor`; an independent read-only SQLAlchemy execution listener captured the DBAPI value `linzhou`. After repair the driver value is `xuning` and the selected grant is absent. The exact variable error required source and driver evidence; it was not automatically diagnosed by the graph.

Ordered evidence and explicit limits are in `diagnosis-evidence.json`, `red-runtime/observations.json`, and `sql-binding-before.json` / `sql-binding-after.json`. The observer was not modified to manufacture a different result.

## Red evidence

The supplied original failures were independently reproduced: 5 failures in the unchanged 16 tests. A real headless browser kept the recipient DOM and original download link open, saw the owner's success notice, and downloaded the same bytes again with HTTP 200. Independent SQLite facts showed the relation remained. The real red recording was stopped and replayed, showing `removed=false` and shared -> shared.

The completed native red inspection passed after normal coding reconciliation. Red verify failed: mapping=failed, state rules=not_run, business=not_run, project checks=failed. The original revocation assertion stopped the observation command, so the not-run categories are not represented as passes. The separate diagnostic runtime evidence is a partial actual observation, not a substitute formal mapping pass.

## Repair and green verification

The existing begin baseline remains immutable. Normal source generation, scan, inspect, verify, accept, and check completed for candidate `514b0b030e8f888f6b3ef8b8bea1c0890c29a03fa3dd6529ba9ee2c40748fc85` and build `9a924db0cb5da491cab831248789b396dc6335178c53a649f70fed36bd2847e7`. Source mappings were refreshed; state and policy declarations and all node/edge IDs were retained.

Implementation mapping, state constraints, business rules, and project checks all passed separately. The unchanged 16 application tests, 84 business assertions across observation on/off/failing modes, and 10 evidence checks passed. The original concurrency, queue saturation, core-only export, retained-recipient, re-share, and missing-transition-witness checks remain in place.

The original browser regression passed 11 steps, and the original revocation browser check passed 12 steps. Its obsolete-recording fixture now points to this copy's **actual red-build recording**, preserving the original old-version hiding assertion without reading the original project's historical artifacts. A supplemental browser case revoked xuning while retaining zhoulan: xuning's unchanged old page returned 403, zhoulan and the owner downloaded identical bytes, and re-sharing restored xuning's download. Real rule events show those decisions at the correct file revision. Its shared -> shared transition is legitimate because one other recipient remains; `removed=true` and the independent grant rows distinguish it from the red failure. All four final recordings have no gaps and were actually replayed. 21 screenshots are preserved, with no browser graph console/page errors in passing checks.

## Archive

- Original instruction, supplied baseline and red records: `request-original.txt`, `diagnosis-baseline-*.json`, `diagnosis-red-tests.json`.
- Original fault source and exact repair: `fault-source/`, `app-service.diff`, `source-repair.json`.
- Independent data and native graph evidence: `red-runtime/`, `sql-binding-*.json`, and their private copy-local SQLite fixtures.
- Red and green graph/verification snapshots: `red-model/`, `red-verification/`, `green-verification/`, copied CLI receipts, `runtime-observations.json`, `graph-maintenance.json`.
- Actual browser operations, screenshots, bytes, and raw recordings: `red-browser/`, `green-regression/`, `green-revocation/`, `green-other-recipient/`. The first replay-loading failure is preserved in `red-browser-attempt-01/`.
- Full repaired source and per-file hashes: `repaired-source/source.zip`, `repaired-source/source-manifest.json`.
- Contract/observer and begin-baseline integrity: `protected-before.json`, `protected-after.json`; 206 protected files remain unchanged.
- Environment setup, mapping attempts, fixes, retests, and measured command costs: `development-costs.json` and its referenced records. The invalid class-support mapping attempt was rejected and reverted; the generator is byte-identical to the pre-fault version. Native validators and projectors were never replaced.

## Run and boundary

Application: http://127.0.0.1:8852/ . Graph: http://127.0.0.1:8853/graph . Run the shared dependency executable with this copy as cwd and `-B run.py --port 8852 --graph-port 8853`. `FILE_SHARING_DB_URL=sqlite:///data/sharing.sqlite3` resolves within this copy. Demo accounts/password are unchanged. Final process ownership is recorded in this copy's `review/running-services.json`.

Current failures: none. This is local scripted acceptance of a controlled diagnosis, with initial design answers still explicitly simulated. No production, independent human, or upstream release acceptance is claimed. Revocation applies to new requests after commit; already downloaded copies and in-flight transfers are outside the stated requirement. No feature expansion, additional fault planting, publishing, or product-material export was performed. Work stops after this diagnosis.
