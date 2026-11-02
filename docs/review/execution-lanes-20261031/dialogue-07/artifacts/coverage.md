# Actual acceptance coverage at freeze

This is an independent AI trial with coordinating-AI business answers. It is not independent human usability testing or an accepted release. Historical passes are not reused as current passes.

| Area | Actual result and evidence |
| --- | --- |
| Canonical upgrade/parity | Passed: 22 normal upgrades, no conflicts; final parity has zero changes/conflicts. |
| Protected files | Passed: 527 pre-upgrade files unchanged, including original application source, assertions, old baseline and historical evidence. |
| Normal configured reports | Mapping, state_rules, business and project_checks all passed; 591 calls closed. `verify-after-config.result.json`. |
| Real browser business flow | Passed login, upload/assign ben, approve, share to cara, identical 101-byte download, no forwarding UI and unrelated-user exclusion. `browser-flow.json`, screenshots and downloaded file. |
| HTTP concurrency/errors | 28 actual HTTP checks; four overlapping upload windows; same-file review race exactly 200/409; rejection, session/input/permission/missing-resource and independent SQLite effect checks. `http-matrix.json`. |
| API/source/data projection | Independently compared eight native Flask routes and eight handler links; exact method/default distinction; no temporary source entries. SQLite columns/FKs saved. `native-api-comparison.json`, `native-database-structure.json`. |
| Complete recording ownership | Passed: 3,265 events, 103 HTTP roots, 1,641 internal point facts. General and data parent checks preserve file identity. `general-ownership-audit.json`, `runtime-parent-audit.json`. |
| Full recording/replay | Actual start/stop, stopped status, no gaps and exact event export passed. Main full recording is separate from the failed-attempt recording and focused recording. |
| Execution/lifecycle display | Four concurrent bands, 28 layer rows; seven overlapping request pairs in separate lanes; 250 data lifecycle slices closed with commit/error meanings. One/all-group collapse and depth/single-layer controls passed. |
| Cursor/navigation | Graph/Timeline cursor and transfer synchronization, seek, keys, play/pause/step in 2D/3D, zoom, interval, loop, overview pan and skip/include passed. This is bounded coverage, not every routing/geometry case. |
| Full source/parameter | Complete file/function-range highlight passed; after actual Load more, the lexical `filename` parameter alone is highlighted. `source-parameter-highlight.json`. |
| Personal settings | Name/note/core, keyboard position/pin, individual hide, reload retention and All elements restoration passed for tested nodes. Full type/view and independent 2D/3D position retention remain incomplete. |
| Observer exclusion | Viewer controls, source browsing, layout, replay and export left all 4,556 live event IDs unchanged in the tested interval. |
| Single-rule focused recording | Actual HTTP/UI check executed. Missing parent entry is a shared limitation and is visibly unassigned; it is not a complete invocation mapping. Latest user permits truthful disclosure in a local recording. See `user-decisions.md`. |
| Excluded builders / scope restoration | Passed separately: one selected builder, zero excluded builders in direct-probe real-app test; actual Web stop followed by another HTTP request confirms normal capture resumes. |
| Negative controls | Passed eight controls: clean mapping, omitted recipient, incorrect revision, missing exit, missing internal-point owner, missing native transition, source drift and real isolated ALTER TABLE schema difference. `negative-controls.json`. |
| Queue boundaries | Ordinary successful stop/drain and pending-zero checks executed. Deliberately queued stop, bounded loss and drain-timeout/interruption variants not run. |
| Projection UI completeness | Presets were selectable. Project/API/code screenshots were sampled before asynchronous source projection completed and show zero visible nodes; these do not establish full projection UI acceptance. Parameter-specific code loading passed separately. |
| 2D/3D geometry/routes | Playback cursor switching exercised. All edge shapes, center/bounding-boundary endpoints, geometry parity, occlusion/routing and every lifecycle link not fully tested. |
| Dragging | Node/group/canvas pointer dragging not completed. Keyboard position changes are not a substitute. |
| View switching/retention | Tested personal reload cases only. Complete type-filter/view and separate spatial preference retention not completed. |
| Graph reload invalidation | Startup after upgrade executed. Actual live graph/build reload and obsolete-recording invalidation not run. |
| Hidden Web / standalone core | Not run in this round. The older core-extracted package is historical evidence only. |
| Acceptance | Not run. Explicit freeze remains active; no business iteration started. |

The remaining items above prevent a complete v1 acceptance claim independently of the user's latest allowance for truthful partial-recording diagnostics.
