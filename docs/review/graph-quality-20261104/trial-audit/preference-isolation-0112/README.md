# Scoped view preference isolation

The controlled live test passed all nine checks on November 4, 2026, 09:28 UTC. Native changes to the conversation's private view did not alter the project default or other protected files. The earlier default-view change remains retained as an unattributed historical change; this result does not retroactively declare that earlier preservation check passed.

## Controlled browser result

[Result](result.json), [driver](check_isolation.py), [private 3D screenshot](scoped-private-3d.png), [before hashes](protected-before.json), [after hashes](protected-after.json).

- Opened the exact previously activated scoped graph URL and restored its custom view.
- Used the native layer ruler to hide Rules, switched 2D/3D, fitted the view, and orbited the 3D camera with a verified empty-canvas mouse drag.
- Observed one successful preference GET and three successful POSTs, all carrying the exact session scope. The private file advanced revision 81→84.
- Preserved all 73 protected files byte for byte: the default plus 51 other original protected files, all 18 recordings, raw observation logs, and the other view namespace. Overlapping sets are counted once.
- Made no application requests, recording changes, source edits, state-model changes, or preference restoration. The private preference file changed through the authorized UI actions.

The first attempt waited for `networkidle`, which is unsuitable for this continuously polling viewer. Its 30 second navigation timeout is retained in [the first receipt](result-navigation-readiness-failure.json). The corrected driver waits for DOM readiness and the actual graph/layout readiness. Both attempts preserved the default and protected data; only the second reached and validated the native gestures.

## Write-path audit

The trial's `integrations/bo_integration.py` imports `GraphSession` and `make_server` directly from `observer_runtime/bo_observer/service.py`. The observer on 8841 is separate from the Flask application on 8041. There is no Flask `request.path` forwarding layer for preference endpoints.

Both GET and POST `/api/preferences` pass the original HTTP handler's `self.path`, including its query, to `BOWeb.preferences_for`. A valid session selects `Preferences(namespace=token)`, whose save path is the conversation file. Seeding from the project default does not write back to that default. The installed viewer injects `createControlBridge.request` into `projectStorage`; this bridge adds the same session parameter to preference GET and POST requests. The live request receipts verified those paths in operation.

The implementation was inspected in these canonical files; no product changes were required:

- `scripts/bo_observer/service.py` and `web/bo_web.py`: query-preserving preference routing.
- `scripts/bo_observer/control/scope.py` and `web/view_preferences.py`: namespace selection and per-file save.
- `assets/stategraph-viewer/conversation-controls.js`, `preferences.js`, and `viewer.js`: scoped storage injection, serialized writes, per-view snapshots.
- `assets/stategraph-viewer/graph-layers.js`, `spatial-layout.js`, and `spatial-renderer.js`: compressed layer heights, derived Y, scoped spatial save.

Paths above are relative to `skills/vibelens/`.

## Earlier default change

The pre-control default hash was `373388afaadd419ef2c2912ea7176d704df48b85cef1f6d7ede8b2ddc8be9853`. Its later hash is `d180e12cf1cd913b29c4c1bf0febcf7ec6d9a8ce6c335ad5ff4b502b0c5306d9`, unchanged by this controlled test. The 16 changed leaves comprise the revision, two visibility lists, two camera arrays and eleven spatial Y values. Planar positions, spatial X/Z and pins were preserved.

The derived Y changes match the saved visibility compression: business 1500→500 and rule nodes 500→0 with gap 500. Layer heights deliberately occupy consecutive visible, populated planes. This explains the Y values, but does not identify the actor that changed the global visibility list.

The default's observed write time was 16:56:41 local. The final and refine drivers were created at 17:02/17:07 and both use the scoped activation URL. Their layer selections, gap and oblique camera also differ from the changed default. The earlier 16:56 inline browser script opened only the business application, not the graph. Another unscoped viewer remains a plausible source, but available evidence does not prove that actor. No default restoration or attribution was fabricated.
