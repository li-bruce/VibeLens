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
| Clean staged Git export | Original [release baseline](clean-export.json) retained; the final viewer upgrade uses separately reviewed receipts and a [fresh export](clean-export-final.json) |
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
a new human dialogue trial are outside this local release-check run. The GitHub
Actions database-vendor job passed separately, together with both source-quality
jobs, Harness and all four OS/Python complete-gate combinations.

The Linux color browser check timed out twice while collecting moving-arrow
frames after switching the expanded recording back to 2D. Its [failure evidence](edge-colors-ci-failure/failure.json)
is retained. The identical check [passed locally](edge-colors-local/result.json),
including a separate software-renderer/CPU-throttled run. The check now preserves
mode, paths, frame counts and animation state on timeout; its frame and exact-color
requirements are unchanged. CI runs this short appearance check before the longer
concept checks so any remaining failure produces diagnostics promptly.

The [diagnostic run](edge-colors-ci-diagnostics/failure.json) confirmed a runtime
bug: the route existed, but each paused cycle painted only its initial pose.
Slow Linux software frames exceeded the wall-clock animation window, and the
repeat timer restarted the cycle before it could advance. Both renderers now use
one bounded presentation clock, retaining at least eight visible increments on
slow frames. The repeat timer waits for the active cycle to finish. Recorded
timestamps, event ordering and source facts are untouched.

The transfer regression now checks frames slower than the entire nominal
duration, normal-speed completion and a fresh cycle's independent start. The
[real Chromium retest](edge-colors-clock-fixed/result.json) passed exact line and
arrow colors, multiple moving poses, both renderers, folding/expansion and the
bilingual legend. [Source quality](source-quality-clock-fixed.json) also passed.
Earlier [pinned Chromium](edge-colors-chromium141/result.json) and
[software/CPU-limited](edge-colors-chromium141-software/result.json) passes are
retained to distinguish the Linux failure from a universally reproducible case.

The [delayed-frame browser retest](edge-colors-slow-frames-retest/result.json)
also passed with every captured frame delayed by 1.4 seconds, longer than the
nominal 1.1-second cycle. The [repeatable helper](slow_frame_retest.py) changes
only frame scheduling, including cancellation; geometry, observations and exact
color assertions are unchanged. Its [first attempt](edge-colors-slow-frames/failure.json)
revealed that the browser readiness helper waited for layout but not source and
route workers. It now waits for all three before inspecting connections.

The viewer change invalidated the two shipped examples' old dependency receipts,
as expected; see the [clean-export rejection](clean-export-clock-fixed.json).
A fresh-baseline attempt was also [rejected](delivery-begin.log), protecting the
already changed dependency from being hidden. The [upgrade review](upgrade_examples.py)
therefore continues the original baseline, verifies byte-identical business
source and independent expectations, and compares the entire graph definition
before and after. The original frozen approvals remain in place. New verified
receipts are published separately as `release-v0.14.0-animation`.

Both example upgrades passed `inspect → verify → accept → check`. The
[upgrade summary](example-upgrades.json) records their candidate identities and
the hashes of preserved application source and independent expectations. The
[package check](package-parity-final.log) verifies that shipped runtime and viewer
copies match the canonical Skill. Original failed exports and the old approvals
remain available alongside the new evidence.
