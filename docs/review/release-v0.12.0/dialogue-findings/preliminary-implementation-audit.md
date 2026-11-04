# Preliminary implementation review

Stage: the fresh release dialogue was still constructing its first implementation.
This is not its final acceptance result. The reviewer read project files and ran
pure checks over saved evidence; it did not edit the trial or execute its application.

[Evidence and SHA-256 identities](preliminary-implementation-evidence.json) records
the initial baseline, its source hashes, the initial observation artifact, the
read-only gate results and later source hashes. The child changed source during
this audit. Runtime findings below refer specifically to
`review/implementation-01/observations-initial.json`, evaluated against the model
and discovery retained in `change/baseline.json`, not later working files.

## Findings

| Finding | Source and evidence | Existing gate / scope |
|---|---|---|
| Unregistered HTTP endpoints are attributed to an error-handler function | Initial `bo_integration.py:137–139` (later snapshot:161–163) falls back to `api:framework_error` for every unknown endpoint. `build_model.py:15` omits Flask's static handler; lines92–93 bind the fallback node to `create_app.framework_error`. A successful `/assets/style.css` would therefore use an error-handler source identity although that handler was not invoked. | The initial static gate already reports `capture_without_feature: api:framework_error`. Adding a case alone would not establish correct source attribution. Exact API qualification checks registered literal route/method/handler combinations; it does not prove that a custom producer's fallback really invoked that handler. Test actual assets and missing routes separately. Keep an excluded technical endpoint excluded, or retain its real technical identity. |
| Review-effect completion lacks its invocation | Initial `service.py:223` emits only `retain_review_record/commit`; the initial adapter wraps business methods, not this effect. The saved on-run has three commit events and zero entries. | **Already caught:** the unchanged conceptual runtime gate reports three orphan completions and missing invocation/completion for both review transitions (seven errors). Static coverage also reports `capture_without_feature: retain_review_record`. Repair the real effect boundary and transaction identity; do not remove these checks. |
| The old-link rejection concept points to an unobserved node | Initial `build_model.py:99` binds `deny_old_link` to `permission`. `service.py:109–117` executes the policy and raises the actual denial, while the adapter records policy graph events, not a `permission` event. The saved 320-event run contains zero events for that node. | **Already caught in this draft:** static coverage reports `capture_without_feature: permission`; once configured as an observed feature, its runtime case must provide a matching node/phase. The concept-binding check alone verifies a real source-backed target, not that every business-effect interpretation occurred. |

The refusal is a branch/result, so fixing its mapping does **not** require an
invented `deny_old_link` function or span. The existing protocol supports an
independent semantic representation with `event_node` and explicit
`lifecycle.bindings.when` over actual captured scalar fields. A truthful refusal
observation must distinguish the relevant download outcome from other errors.
The generic `BusinessError` class alone does not do that. Conditional selectors
are checked against the actual owner's capture fields (`bo_contracts.py:560`);
the viewer derives only registered intervals (`trace-lifecycles.js:163`).

## Semantic limits to verify after normal checks

`notify` means **the recipient sees a persisted site message**, so mapping it to
dashboard reading is not inherently wrong. However, the initial evidence contains
both an uploader dashboard with zero messages and a recipient dashboard with one
message. An unconditional dashboard mapping alone cannot distinguish the two.
Its focused graph/recording check should use the relevant actual actor/result.

The confirmed `download` operation means **starting a new download**. Its current
span ends after authorization and opening the file, which fits that scope. This
review does not demand a fabricated whole-transfer duration. A claim about stream
completion would require its own real completion boundary.

The initial data has 16 collector transport validation errors and empty read-basis
results. These remain failed/incomplete evidence while the child performs its
normal checks. They are not a final trial verdict or evidence to weaken a gate.

## Guidance and framework distinction

The installed Skill already requires actual source/function boundaries, real
framework responses and independent evidence (`SKILL.md:49,82,92,100`;
`references/telemetry.md:236–250`). Its lifecycle guidance explicitly separates
specific denials from a shared exception class and permits registered semantic
representations (`references/lifecycles-and-representations.md:21–24,53–60`).

For this draft, effect closure and declared capture omissions are implementation
issues detected by existing checks. The broader remaining validation boundary is
semantic attribution: a source-backed binding or an actual HTTP status alone does
not prove that a conditional business effect occurred, or that a custom fallback
used the correct handler identity. Preserve focused positive and negative runtime
witnesses for those meanings before calling the mapping complete. No frozen
framework code was changed by this preliminary audit.
