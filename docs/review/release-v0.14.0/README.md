# VibeLens v0.14.0 release review

Date: 2026-11-08 (Asia/Shanghai).

The release integrates `feat/concept-flow-layout` through `c6525669` into `main`.
All nine feature commits remain in history. Release metadata, installation links
and the Pages version are updated together; historical evidence retains its
original versions and bytes.

## Validation

| Check | Result |
| --- | --- |
| Complete default repository gate | Passed in 468.91 seconds; [receipt](full-gate.json), [output](full-gate.log) |
| Maintained-source syntax, lint and formatting | Passed for 182 Python and 128 JavaScript modules; [receipt](source-quality-accepted.json), [output](source-quality-accepted.log) |
| Clean staged Git export | Both accepted examples passed with their original frozen approvals; [report](clean-export.json) |
| Extracted Harness plugin | Five checks passed against the real pinned registry/invocation runtime; [report](harness-runtime.json) |
| Staged installation bytes | All 389 canonical Skill files match the tested archives and Git index; [report](staged-package-parity.json), [checksums](SHA256SUMS.txt) |
| Concept networks and live capture | Seven checks passed: 34 concepts, 14 mappings, definitions, 2D/3D, recording and Timeline; [report](concept-browser-retest/run-d91f44e56978/result.json) |
| Lazy-source identity comparison | Seven checks passed after checking the immutable server model separately from declared source projections; [report](concept-browser-source-pass/run-ca12a54f6004/result.json) |
| Product home and walkthrough | English and Chinese, five scenes, custom-view persistence and 3D camera dragging passed; [report](pages-browser-final/result.json) |
| Complete walkthrough regression | Both languages passed five stages, eight native presets, seven layers, 494 source nodes, saved-view restoration, real transfer animation and rotate/zoom/pan; no browser errors; [report](case-browser-pass/summary.json) |
| API response observation | Three checks passed for exact GET/POST identities, recorded HTTP 403 and cross-layer causality; [report](api-browser/results.json) |
| Concurrent execution and Timeline | Six checks passed with 33 recorded events, two execution groups and ten layer rows; [report](execution-browser/result.json) |
| Chapter interaction | Native editor/viewer focus preserves the current chapter; page scrolling and explicit navigation release it; [report](scroll-browser/result.json) |

The default gate includes deterministic distribution builds, canonical file
checks, SkillHub materialization/tamper refusal, native execution and observer-free
exports. The Harness check uses Node.js 24.9.0 and Harness 0.2.2-rc.1; it exercises
the actual registry and native invocation with fixture sessions, not an LLM trial.

The browser tests found and corrected Pages integration gaps after the
viewer toolbar changed: the story still invoked the removed `show-all` control,
and its advertised 3D drag gesture inherited marquee selection. The story now
uses the shared layer control and explicitly selects the native orbit tool.
Preset-specific actions keep their selected layers. Restoring a saved story view
also excludes the new unsaved `custom-draft` entry. The original timeouts are
preserved in [first attempt](pages-browser.log) and [second attempt](pages-browser-retest.log).

Full-tool exploration exposed a separate chapter-selection race: native iframe
focus could scroll the page into the preceding chapter, which then restored its
saved view over the developer's selection. The scroll controller now keeps the
active chapter while its shared viewer owns the interaction. Explicit navigation
and page wheel/touch gestures release that ownership. The dedicated browser
regression checks both persistence and release; the walkthrough also asserts
chapter stability while switching all eight native view presets.

The more detailed walkthrough check now compares the exact displayed glyph and
region IDs, rather than counting hidden source-boundary boxes in the full layout
inventory. It anchors each chapter at its start, matching the actual chapter
navigation instead of treating a partly visible neighboring chapter as selected.
The earlier [inventory assertion](case-browser.log), [saved-view failure](case-browser-retest.log)
and [chapter-switch timeouts](case-browser-final.log) are retained, including the
[attempt showing that scroll alignment alone was insufficient](case-browser-accepted.log). Maintained
browser checks also use the current keyboard context menu and shared layer action
in place of removed toolbar controls. Their original feature assertions remain.

The feature-branch CI also found an outdated concept-browser assertion. A shared
native/concept identity deliberately preserves native capture authority; checking
only `origin=concept-design` rejected valid merged definitions. The check now
compares visible concept IDs and complete confirmed definitions exactly, and opens
details using the current keyboard context-menu action. The [original failure](concept-browser-ci-failed.log)
and [screenshot](concept-browser-ci-failed.png) are retained. No model, business
expectation or acceptance gate was changed to pass these checks.

The first main-branch Linux browser run exposed another timing-dependent test
assumption: the initial UI inventory can contain a partial source slice, while
opening all layers loads additional real declarations. Comparing the two raw
arrays treated that documented loading behavior as a model mutation. The check
now waits for source readiness, compares the independent server model before and
after exactly, and requires the displayed model's IDs to equal the authored IDs
plus declared source projections. Its [Linux failure](main-ci-browser-failure/browser.stderr)
and [screenshot](main-ci-browser-failure/failure.png) remain available; the final
local retest again passed all seven checks and actual upload/share capture.

The first Harness invocation used the system Node 20 and missed the isolated
pinned host packages. Its [failure](harness-runtime-missing-environment.log) is
retained; rerunning with the existing Node 24.9.0 host passed. Safe tar extraction
also needed to run outside the Windows sandbox because `realpath` was denied;
the archive safety filter remained enabled.

A local formatter invocation without the repository configuration produced a
format-only [failure](source-quality-final.log). Applying the committed formatter
configuration resolved it; the final source-quality receipt above passed.

Existing implementation evidence:

- [Native integration and directional layouts](../2026-11-06-coupling-flow/README.md)
- [Concept networks and in-panel explanations](../2026-11-06-concept-details/README.md)
- [Viewer interactions](../2026-11-06-viewer-interactions/README.md)
- [Expansion and relation identity](../2026-11-06-expansion-relations/README.md)
- [Node-type connection styles and real replay](../2026-11-06-relation-strokes/README.md)

The final walkthrough run includes the saved-view and chapter-selection repairs.
It also retained the existing narrow-marketing-page checks; this release adds no
mobile adaptation to the graph application.

The release preserves stable model identities, native business definitions,
saved views and frozen example approvals. Database-vendor container suites and
a new human dialogue trial are outside this release-check run.
