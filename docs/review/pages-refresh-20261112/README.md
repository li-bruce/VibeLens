# VibeLens Pages refresh

Baseline: v0.14.0 (`ab211795`). Branch: `feat/pages-v014-refresh`.

## Scope

1. Replace double-rail relationships with continuous single strokes in the shared
   2D/3D renderer and legend. Keep endpoint, layer, identity and playback semantics.
2. Present the current product through concise bilingual copy and focused views.
3. Keep the file-sharing story: confirm the model, record a run, inspect the
   revocation path, ask AI to fix the source, and verify the updated implementation.
4. Remove blocking/repeated recording downloads from the parent page. Show actual
   loading phases, retain the previous view during chapter changes, and allow retry.
5. Verify browser interactions, both languages, recorded evidence, managed example
   parity and publication. No changes to captured business facts.

## Findings before changes

- Mapping/reference and synchronization relationships used offset parallel rails.
- The parent demo fetched both full artifacts (8.56 MB total) before rendering its
  conversation; the embedded viewer then fetched its selected artifact again.
- The story already uses the canonical viewer. Layout improvements must use its
  actual presets, graph filtering and layout, rather than a separate drawing.

## Execution

- [x] Shared single-stroke implementation and CPU buffer regression (20,000 edges).
- [x] Actual 2D/3D line, arrow and legend checks.
- [x] Home and demo content, layout and loading.
- [x] Browser regression, screenshots and measured loading evidence.
- [x] Managed example synchronization and package checks.

Publication uses the existing GitHub Pages workflow on `main`. Check the workflow
run and public page resources after pushing the reviewed change.

## Result

The shared renderer now uses continuous single strokes. Mapping edges use an open
arrowhead; synchronization and indirect relationships use a subtle border. Layer
colors and endpoint-type solid/dashed distinctions remain consistent in both
renderers, moving arrows and legends. All seven relationship families retain a
distinct appearance. Rendering 20,000 edges still uses two line batches.

The homepage explains the confirmed business/state/rule models, navigation to
implementation, recording and iteration. The five-stage demo uses the real viewer,
shorter captions, native clustered layouts, a shared-rule view and a compact source
investigation. Native screenshots include their build, node IDs, event and hashes
in [capture-proof.json](../../site/images/capture-proof.json).

The parent page loads only a conversation summary. The viewer loads the selected
recording on demand and reconstructs all its original fields. No archived source,
event, graph identity or application result was rewritten.

| Payload | Before | After |
| --- | ---: | ---: |
| Parent conversation input | 8,555,618 bytes | 173,458 bytes |
| First recording | 3,053,084 bytes | 2,073,025 bytes |
| Updated recording, loaded when requested | 5,502,534 bytes | 4,171,617 bytes |

These are file sizes, not compressed transfer sizes or public-network timings.
The parent input is approximately 98% smaller. Loading phases, a slow-load message
and retry cover delayed or failed requests; same-document chapter changes retain
the existing canvas. The homepage layer explorer also has loading feedback.

## Verification

| Check | Result and evidence |
| --- | --- |
| Shared strokes and colors | `test_relation_strokes.mjs`, `test_edge_colors.mjs` and `test_layered_view.mjs` passed; 2,688 color/type combinations and 20,000-edge buffer construction |
| Rendered lines, motion and legend | [2D/3D browser evidence](edge-colors/result.json), including folded and expanded nodes |
| Original data preservation | `test_case_transport.mjs`, `test_case_artifacts.mjs` and `test_file_story.mjs` passed; exact decoded records and independent mutable copies |
| Complete bilingual walkthrough | [Five stages in both languages](browser/summary.json), source inspection, moving arrows, eight presets, seven layers, 494 code nodes and saved views across the iteration |
| Fresh loading | [Six fresh contexts](startup/result.json), three per language, with delayed data and one retained iframe across chapters |
| Failure recovery and shared rules | [Final loading checks](loading-final/result.json): HTTP 503 followed by successful retry, ten connected rule nodes and no eager second-recording download |
| Home and demo page interactions | [Final page checks](site-final/result.json): English/Chinese, screenshots, image switching, interactive layers and reduced motion |
| Source checks | [Formatting and source validation](source-check.json): 182 Python modules and 129 JavaScript modules |
| Managed example updates | [Both examples verified](upgrade/example-upgrades.json); application files and graph definitions unchanged, previous receipts retained |
| Packaged runtime copies | `tools/check_package.py` passed: 199 copied runtime modules match |
| Clean checkout acceptance | [Staged Git export](clean-export.json): both examples passed with frozen receipts, without regeneration or reapproval |

## Failures found and corrected

1. A native preset restored the selection tool after entering 3D, so a scripted
   orbit gesture did not rotate. The compact presentation now restores Orbit after
   the preset has settled. Screenshot capture asserts both the tool and an oblique
   camera; full-tool mode retains the developer's selected tool.
2. The product-control section contained two links to the same demo. Its browser
   check rejected the ambiguous interaction. The redundant call to action was
   removed, and the unchanged interaction check passed.
3. A five-node investigation spread too far under the large-graph cluster layout.
   It uses the native directed layout; broader business and rule views retain the
   cluster layout. Source and layer screenshots were recaptured through real UI
   controls, keeping the same compact investigation across the 2D and 3D images.

## Boundaries

Browser results use local Chromium with software WebGL. Delayed/failed responses
test the loading behavior; they do not establish an internet latency or hardware
frame-rate guarantee. The 20,000-edge check measures CPU buffer construction and
batch count, not interactive FPS. Existing small-screen marketing checks were
preserved; this change adds no phone-specific graph-tool functionality.

The earlier [baseline](baseline/result.json) and intermediate runs are retained.
The latest final browser results and screenshots are the acceptance evidence.
