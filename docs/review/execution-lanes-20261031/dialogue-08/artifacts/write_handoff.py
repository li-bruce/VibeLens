"""Write the explicitly requested frozen review handoff from retained evidence."""
import json
from pathlib import Path
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
def read(name):return json.loads((OUT/name).read_text(encoding="utf-8-sig"))
def write(name,text):(OUT/name).write_text(text,encoding="utf-8")
audit=read("final-audit.json")
budget=read("control-budget-audit.json")
ports=read("port-geometry-audit.json")
source=read("source-layer-audit.json")
routes=read("geometry-routes-checks.json")
pointers=read("geometry-checks-attempt4.json")["checks"][:7]
(OUT/"geometry-acceptance.json").write_text(json.dumps({"valid":True,"build_id":audit["build_id"],
    "pointer_checks":pointers,"pointer_source":"geometry-checks-attempt4.json: seven successful checks preceding its separately corrected route-driver failure",
    "routes_and_filters":routes,"port_geometry":{"valid":ports["valid"],"checked_endpoints":ports["checked_endpoints"],"matches":ports["matches"]},
    "limitations":audit["limitations"],"claim":"Bounded actual geometry/UI checks; historical driver failures remain unchanged."},indent=2),encoding="utf-8")
audit["acceptance_ready"]=False
audit["acceptance_status"]="frozen_before_accept"
audit["shared_blocker"]={key:budget[key] for key in ("classification","response_bytes","fixed_cli_budget","real_cli_result")}
(OUT/"final-audit.json").write_text(json.dumps(audit,indent=2,ensure_ascii=False),encoding="utf-8")
write("shared-control-activation-gap.md",f'''# Shared control activation failure

## Actual reproduction
The current real `/api/view` returns HTTP 200, current source binding, {budget['events']} retained events and {budget['response_bytes']:,} response bytes. Canonical `bo_control.py activate` fails with `Observer response exceeds the inspection budget`. Installed control CLI bytes match the maintained canonical CLI (SHA256 `{budget['cli_sha256']}`).

```powershell
$projectPath = 'C:/Users/Lvi_P/Documents/Work/CF/平台软著/VibeLensTrials/execution-bands-dialogue-20261031-03'
& "$projectPath/.venv/Scripts/python.exe" -B -X utf8 "$projectPath/observer_runtime/bo_control.py" activate --root $projectPath --url http://127.0.0.1:8983 --message '$vibelens'
```

The final user instruction freezes this round; do not restart the application in this frozen trial. `final-view.json` and `control-budget-audit.json` retain the real large response/evidence. A later authorized conversation can reproduce after normal service startup and real retained-event accumulation.

## Cause and ownership
`observer_runtime/bo_observer/control/cli.py:27-32` enforces {budget['fixed_cli_budget']:,} bytes. Activation at lines 60-64 unconditionally loads the whole `/api/view` just to establish project identity. Non-activation commands also use this full view; the existing snapshot option does not apply to activation. Normal legal event accumulation therefore disables conversation control. This is a shared control-interface functional defect, separate from the application, recorder, renderer and corrected test-driver mistakes.

Do not clear events, fabricate a small live response, raise this trial's limit, call lower-level authorization directly, or modify managed files. Repair the canonical transport/metadata boundary with bounded reads and intact project/conversation validation; regress large normal views and wrong-project responses. Then use the normal upgrade interface in a newly authorized continuation.

## Evidence and acceptance boundary
- `activation-current.command.json`, `.stdout.log`, `.stderr.log`: exact real failure.
- `control-budget-audit.json`: actual response size/hash, current build/binding/health, canonical parity and zero observer-induced business events.
- `final-view.json`, `final-recordings.json`, `raw-recording-*.json`: retained runtime evidence.
- Current candidate `{audit['candidate_id']}`; runtime build `{audit['build_id']}`.
- Four normal reports and business/Web checks pass within the coverage below. **No accept or final accepted check was executed.**
''')
write("coverage.md",f'''# Current-version coverage at explicit freeze

This is an independent AI trial with coordinating-AI business answers. It is not human usability testing or an accepted release. The user explicitly froze this round after the shared control failure was confirmed.

| Area | Current evidence and result |
| --- | --- |
| Upgrade | Passed: 16 files through normal upgrade, no conflicts. No managed-source hand edits. |
| Preservation | Passed: {audit['protected_files']} frozen prior files and all original {audit['original_protected_files']} protected files unchanged; baseline SHA256 `{audit['baseline_sha256']}`. |
| Normal gate | Mapping, state_rules, business and project_checks passed for candidate `{audit['candidate_id']}` in `verify-current.result.json`; 591 calls closed. |
| Browser business | Passed current-build upload/assign Ben, approval, sharing to Cara, identical 101-byte download, no forwarding form and unrelated-user exclusion. `browser-flow.json`. |
| Concurrency/errors | Passed 28 real HTTP checks, four overlapping upload windows, one-file review race exactly 200/409, rejection/session/input/permission/missing-resource/rollback effects and independent SQLite reads. `http-matrix.json`. |
| Full collection | Passed {audit['full_events']} full events, {audit['full_http_roots']} actual HTTP roots, zero interval gaps and no context-only substitutes. Native data/general point parent audits retain file identities. |
| All layers/relations | Passed loaded nine-layer inventory and explicit cross-layer relations. `source-layer-audit.json`; native API independently matches eight Flask routes and handler links. Static links are not execution proof. |
| Loaded projection UI | Passed actual nonempty project/API/code views (25/68/180 visible nodes in the retained current viewer run), states/business/data views, full source and lexical filename highlight. No premature zero-node image is treated as passed. |
| Exact parameters | Passed complete source with exact token highlights for upload reviewer_id/filename, review decision and share recipient_id. `source-layer-audit.json`. |
| Pointer and personal views | Passed actual 2D node/region-caption/group/canvas drag, 3D node/region-label/ray drag and camera pan, branch-coordinate movement and independent 2D/3D coordinate retention across switching/reload. `geometry-acceptance.json` preserves the successful attempts' provenance. Existing note/core/hide/pin/name reload cases passed in `viewer-checks.json`. |
| Routes and layers | Passed actual rendered straight/curve/orthogonal/bus routes in both dimensions; original relation IDs and separate owner-bound projection guides retained. Layer visibility and type filters survive reload; populated plane spacing is uniform. {ports['checked_endpoints']} retained endpoints independently match their exact owner's node center or region boundary/plane. `port-geometry-audit.json`, `geometry-routes-checks.json`. |
| Route limit | Explicitly disclosed: 3D orthogonal and bus each report two blocked review_file self relations in the retained manual layout. Their original relations remain accessible; straight/curve render them. This is the documented bounded-search gap, not a claim that every route is clear. Straight/curve intersection counts also remain in raw diagnostics. |
| Lifecycle links | Passed 1,304 lifecycle fragments, 263 vertical and 169 horizontal rendered links with call/return/observation/data/completion/transition kinds; actual committed and exception meanings. `lifecycle-links.json`. |
| Replay controls | Passed execution bands/concurrency separation, group collapse, depth/single-layer, seek/keys/play/pause/step, Graph/Timeline cursor and transfer sync in 2D/3D, interval/zoom/loop/pan/skip/include and exact raw-event export. `viewer-checks.json`. |
| Focused recording | Passed one selected permission decision with four witnessed HTTP/access boundary headers, one invocation group and zero unassigned observations. One ordinary selected step plus initial/final snapshots; excluded value builders zero; normal capture restores after stop. `focused-boundary-audit.json`, `focused-capture-result.json`, `builder-audit.json`. |
| Focused evidence limit | Pre-start context is explicitly limited to the latest 2,000 prior events. Unselected values were not collected. Do not call this complete business collection or infer earlier parents. The selected interval has actual retained ancestors and no ownership gap. |
| Queue boundaries | Passed real delayed-native-transport queued stop/drain, actual timeout and bounded loss. Timeout/loss retain interrupted recordings/gaps while actual download succeeds; stop restores full capture. `queue-cases.json`, isolated copies under `.tmp`. |
| Observer exclusion | Passed: source/view/layout/replay/export, layer/type and Web-mode controls add no business events in their tested intervals. Control-budget diagnostic is also read-only. |
| Actual graph reload | Passed actual same-browser exit from old replay and old-option removal after normal rebuild/owned producer restart. Canonical API rejects obsolete recording with HTTP 400 and explicit earlier-version error; old raw hash unchanged. Initial driver incorrectly expected 404; failure and independent response recheck retained. `graph-reload.json`, `reload-api-rejection.json`. |
| Hidden Web | Passed real Web disabled status for graph/view while actual upload/review/share/download and denial continue, then original mode restored. `hidden-web.json`. |
| Standalone core | Passed normal core export after normal ownership seal, executed in a separate process under this round's `.tmp/core-extracted`, real handlers/SQLite/download/denial and no observer import. `core-execution.json`, `core.zip`. |
| Negative controls | Passed missing recipient, wrong revision, missing exit, missing internal-point ownership, missing native transition, source drift and real isolated schema ALTER detection, plus clean control. `negative-controls.json`. |
| Conversation controls | **Failed shared interface**: actual {budget['response_bytes']:,}-byte normal view exceeds CLI {budget['fixed_cli_budget']:,}-byte full-view budget. Activation fails; inspect/plan/apply have the same full-view dependency but were not separately executed after this blocker. `shared-control-activation-gap.md`. |
| Acceptance | **Not run**: explicit freeze before accept. No final accepted-state `check`; no business iteration. |

Coverage is bounded to these real recordings/layouts and finite UI cases; it does not prove all geometry, performance or human usability. Drag-reorder/layer-gap modification across upgrades and every custom-view/menu combination were not exhaustively tested. No fabricated wait/cancellation/activity model was added to the confirmed flat file workflow.
''')
write("RESUME.md",f'''# Latest frozen continuation checkpoint — 2026-11-01

Read this directory first. Older RESUME files are historical. The user explicitly froze this round after confirming the shared control interface defect. **Do not restart, accept, upgrade, or begin business work until a new conversation is authorized.** No accept was executed.

## Preserve the same active change
- Continue `resume-first-integration-20261031`; never begin a replacement or replace its baseline.
- Baseline SHA256 `{audit['baseline_sha256']}`.
- Candidate `{audit['candidate_id']}`; runtime build `{audit['build_id']}`.
- U001/U002, drive mode, Python/SQLite, synthetic accounts and confirmed role/permission/state meanings remain unchanged. Business answers are coordinating-AI simulations.
- {audit['protected_files']} prior files and all original {audit['original_protected_files']} protected files remain unchanged. Assertions and historical raw recordings are intact.
- Shared sources and installed managed files remain read-only except normal upgrade. Current source changes are project output/scratch routing in `tooling/observe.py` and normal ownership sealing; no business source edits or policy changes.
- New normal observations route to this round; the next authorized retest needs a new directory/output route. Scratch stays under that round's `.tmp`.

## Blocking maintenance issue
Read `shared-control-activation-gap.md` and `control-budget-audit.json`. The real current view has {budget['events']} retained events and {budget['response_bytes']:,} HTTP response bytes. `bo_control activate` unconditionally reads it with an 8 MiB cap, fails and cannot use `--snapshot` for activation. Maintained and installed CLI bytes match. Do not reset events, raise local limits, bypass scope validation or patch managed files. Maintenance must repair the canonical interface, then a newly authorized conversation upgrades normally.

## Retain completed evidence
The four configured reports, real browser/HTTP flow, concurrency/review competition/errors, full/focused recording, source/parameter/layer projections, pointer/preferences, lifecycle/replay, queue boundaries, Web disable, standalone core and negative controls all have current evidence. See `coverage.md`. Do not rerun unaffected entire suites after the control-only repair. Required retests then are normal upgrade parity/build/gates and actual large-view activation/control behavior, plus anything affected by the canonical fix.

Full recording `38bb643f475142f8a970f32d8645b0ca` has 5,629 events and no gaps; actual HTTP roots 103. Focused captures have one selected decision and witnessed parent boundaries, while the 2,000-event pre-start context limitation stays disclosed. 3D orthogonal/bus each expose two blocked self relations; straight/curve remain available. No universal geometry claim is made.

Driver failures remain: stale candidate review, sandbox service connectivity, wrong graph property, async source/route repaint waits, snapshot-step count, pre-context-limit assertion, delayed restored-event arrival, region/overlay pointer targeting, hidden accessibility-layer buttons, condition-vs-decision selector, expected 404 vs actual canonical 400 and scratch callback-source identity. These were corrected only in project/review scripts and are separate from the shared CLI defect.

## Freeze state
`freeze-manifest.json`, `freeze-verification.json`, consistent `sqlite-snapshot.sqlite3` and `source-runtime-snapshot.zip` describe the final preserved state. Credentials/session secret, dependency cache, personal view/control files and scratch copies are not in the ZIP; their originals remain on disk. Historical review trees are not rewritten. `owned-services-at-handoff.json` and the subsequent freeze stop receipt identify only this round's owned service. Keep the synthetic database and session secret.
''')
write("user-decisions.md",'''# Current conversation authority

The initial request explicitly reauthorized continuation, lifted the previous freeze, retained the same active change/baseline and authorized current-version local business/Web acceptance. It also required stopping before accept on a real shared framework/Web defect and passing it to maintenance. No business meaning changed or required another question.

The latest coordinating conversation instruction explicitly freezes this round:

> 维护源码已确认：control/cli.py 的 activate/inspect/plan/apply 为取得图模型，会读取整个 /api/view，再受统一 8 MiB 限制；正常事件积累因而会让图控制失效。这是共享控制接口的功能缺陷，不能靠清空记录、抬高预算或改演示绕过。请停止在 accept 前，保留当前所有通过证据、预算失败及正常业务源，冻结本轮并写 RESUME/coverage（标清未通过的控制项及路由限制）。不要修改受管源码、不要开始业务迭代。维护会话修复后再用新对话继续，未受新改动影响的项目保留证据即可。

No accept, final accepted-state check, business iteration or managed-source workaround was performed.
''')
with (OUT/"progress.md").open("a",encoding="utf-8") as stream:
    stream.write("\n- Final current normal gate and independent audit passed; 838/527 protected bytes and original baseline preserved.\n- Shared control activation failed on the actual normal large view. Canonical and installed CLI match; no bypass. Maintenance confirmed the defect and explicitly froze this round before accept.\n- RESUME/coverage/shared-gap report written; retain all unaffected passes for the next authorized control-only retest.\n")
with (OUT/"task_plan.md").open("a",encoding="utf-8") as stream:
    stream.write("\n## Explicit final freeze\nPhases 1–4 have bounded real evidence as cataloged in coverage.md. Phase 5 stopped before accept by direct instruction because canonical conversation control fails on the normal large view. Preserve unchanged passed checks; no business iteration. Freeze artifacts and owned-service shutdown remain the final preservation actions.\n")
print(json.dumps({"status":"frozen_before_accept","shared_blocker":"control_budget","reports_written":True,"baseline_unchanged":True}))
