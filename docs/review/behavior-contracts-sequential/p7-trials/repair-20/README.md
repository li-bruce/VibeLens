# Repair 20 — API projection identity

The Node trial completed its original browser flow and two normal recordings.
The full post-recording verification passed. Independent desktop checks passed
six locale reloads and seven presets in 2D/3D, then stopped when Timeline could
not select the recorded run. This is a viewer failure, separate from the passed
native assertions and capture validation. P7 remains in progress.

## Failure and cause

The recording request returned HTTP 200 with no browser exception. The UI
reported that the graph belonged to an earlier version. Source build, model
hash and concept revision matched. Every API projection field also matched
except `revision`; a subsequent read changed that revision again.

`CodeGraph.api_snapshot` inherited the complete source index revision. That
index includes the project tree, so an unrelated document could invalidate an
unchanged API. `api-before.log` reproduces this with a real project file change:
the source build and API nodes stay equal while replay identity changes.

## Repair and boundaries

The API revision now hashes its own endpoints, observation edges, source
bindings, aliases, migrations and diagnostics. The whole-project discovery
report remains available as `scope`, outside this API identity. The full source
index retains its own revision and checks.

The viewer's source/model/API/concept compatibility checks are unchanged. Tests
retain invalidation for method, route, handler, documentation, capture-contract
and selector changes. Historical recording bytes and revision fields are not
rewritten. The fixed provider requires fresh native trial captures before final
acceptance; earlier runs remain review evidence.

A separate presentation review found `inactive` copied into the Chinese state
name even though the node had a Chinese explanation. Skill guidance now makes
the precedence of model-qualified state/event names explicit. The trial will
correct its names through the normal metadata workflow; machine values and
event identities remain unchanged.

## Evidence

- `api-before.log`: original failing file-change regression.
- `api-after.log`: seven API snapshot tests after the implementation change.
- `targeted.log`: 65 API, source-index and native lifecycle tests passed.
- `first-desktop-failure.zip`: original independent checks, screenshots,
  displayed error, identity comparison and exact diagnostic runners.
- Later regression, installation and trial results are added after execution.

This repair does not mark either trial or P7 accepted.

## Completed repair gates

Full regression passed: 1296 reported tests in 116 unittest reports, with 1 existing skip(s). These totals include repeated suites. The 65 targeted tests and unchanged viewer compatibility checks passed. Both managed examples passed verification, acceptance and subsequent checks. The fresh installation matches all 463 owned files and passes three installed API identity cases. The staged clean export passed without regeneration or reapproval. See `results.json`. Native trial acceptance remains pending.
