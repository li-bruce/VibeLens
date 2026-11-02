# Typed focus and original path boundaries

Trial 10 reached the real scoped page and applied its first chain view, then the
same four anchors with depth two and business/decision filters failed. The planner
expanded neighbors without checking node types. It required `state_new`, which
the viewer correctly hid. The visible-node check rejected the plan. Keep that
check and the exact failing request.

- `control-types-negative-01.log` reproduces an excluded state entering ordinary
  neighbor expansion on a generic model. All original tests remain intact.
- The first prototype filtered every path by type. Its 22 unit tests passed, but
  `control-types-real-replay.json` showed it could choose a different path and
  remove the recipient bridge. It was not released or accepted. Preserve that
  evidence as an insufficient intermediate implementation.
- The final planner retains the original ordered path. Necessary cross-type
  bridges are explicit `context_node_ids` under the viewer's existing one-hop
  boundary contract. Only ordinary neighbor expansion follows requested types.
  Unsupported longer hidden chains fail before publication, retaining every
  original edge instead of inventing a direct shortcut.
- `control-types-retest-02.log` passes 22 control tests: original strict checks,
  typed neighbors, cross-type paths, malformed context and actual Python/JavaScript
  view-membership parity. `control-types-http-retest-01.log` passes all ten
  capture/session/standard-HTTP tests.
- `control-types-real-replay-02.json` uses byte-identical original inputs and the
  same anchors, depth, direction and filters. It retains the original four
  business-chain relations and selects 16 nodes with three explicit bridges:
  pending, approved and designated recipient. Unrelated excluded neighbors remain
  omitted boundaries. This is selector replay, not fresh application/UI acceptance.
- Existing runtime and design browser suites pass in
  `control-types-browser-host/result.json` and
  `control-types-design-browser-host/result.json`, retaining 2D/3D, saved views,
  replay filters, unchanged observations and scoped controls.
- Source gate 15 passes for 121 Python and 90 JavaScript modules. Both managed
  examples are verified and frozen. Full repository gate 11 passed on November 1
  at 04:21:47 +08:00, with the recorded canonical selection hash unchanged.
  Trial 11 then passed its v1 acceptance and normal project entrypoint. Its real
  page retained the requested four anchors, depth, direction and node filters,
  including the three required bridges. No original verification requirement was
  removed. The selector replay above remains distinct from that fresh UI test.
