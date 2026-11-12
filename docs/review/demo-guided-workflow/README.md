# A continuous developer walkthrough

## Goal

Rebuild the bilingual Pages demo around one developer's file-sharing application:
request, confirmation, first build, broad observation, focused investigation,
AI-assisted repair, and repeat observation. Keep the real viewer and archived
execution records. This change concerns the guided presentation, not application
behavior or the observer protocol.

## Story and interactions

1. Describe the application in ordinary language. Reveal the clarification and
   answer, then review business, state and rule diagrams before confirmation.
2. Finish the first coding round. Show the application alongside the connected
   graph; explain which surface is used for development, operation and observation.
3. Demonstrate recording an operation with business and state nodes visible.
   Explain node activation, moving arrows and changed values. Stop, replay and
   scrub the captured sequence to identify the unexpected unchanged access.
4. Follow that finding into the revocation's inputs, function and storage result.
   Reveal one scope at a time. Source inspection is optional; it never opens
   automatically. Save a focused view for the next run.
5. Describe the observed problem to AI. Show the repair conversation and the
   updated implementation mapping. Preserve the confirmed business requirement.
6. Replay the same actions after the repair, compare actual effects, and show how
   this observe–refine loop continues through development.

## Evidence boundary

The Pages demo uses scripted conversation, captured application screens and actual
archived execution events. Its recording walkthrough illustrates the product
controls using that existing sequence; it does not run a backend or create new
runtime facts. The example defect and fix are already documented in
`docs/review/file-sharing-demo`. Keep original event, node and relation identities.

## Baseline findings

- The headline introduced a defect before explaining the application.
- The initial conversation jumped directly into running an implementation.
- The running chapter started playback before explaining recording or its scope.
- Investigation immediately opened a large source panel, skipping the transition
  from a business-level observation to parameters and storage effects.
- Past conversation, application controls and viewer controls competed for space.

## Checks performed on 2026-11-12

The shipped recording and original source archives are unchanged. Unit checks
pass for the six chapters, all selected node identities, exact playback bounds,
state/policy confirmation, original source bytes and bilingual copy. ESLint,
Prettier, Python syntax/format checks and the Pages viewer build also pass.

The interactive acceptance was performed in the Codex browser at
`http://127.0.0.1:8916/demo.html`, using the actual controls and captured records.
The repository's standalone browser test was updated for this journey and syntax
checked; it was not executed in this session.

### Findings, repairs and retests

| Finding during inspection | Repair | Retest |
| --- | --- | --- |
| The confirmation thread and model overflowed a laptop-height viewport | Bound the conversation height and reduce desktop spacing | Three model tabs and confirmation remain usable |
| A clicked application action was counted before its record was selected | Require an acknowledgment containing its original event ID | Both versions reach 3/3 only after the selected events appear |
| Data scope tried to open a live code index while replaying an archive | Reuse the source neighborhood already attached to that recording | The mapped function and complete source open without a loading error |
| Broad containing regions engulfed the detail view | Use a narrow flat selection, real mapping edges and saved initial positions | State, input, operation, data and source groups are separated |
| Omitting source-file/class node types also hid their function | Retain the physical containment path and place it alongside the operation | File, class, function and mapping relations are visible |
| A coarse replay could step beyond the final selected action | Clamp to the original final action ID before stopping | The final recipient decision remains the end of the sequence |
| Custom-view labels described a broader scope than the current investigation | Reuse the same input, storage/source and state groups as progressive inspection | Hiding states keeps the function, values, storage target and their actual relations |

### Browser evidence

- Chinese confirmation: progressive replies and business/state/rule tabs.
- Recording: start, three application actions, stop, play, keyboard seeking.
- Inspection: three depths; source appears only after the explicit source button.
- 2D/3D switching and pointer drag in the three-dimensional canvas.
- English switch preserves the selected chapter.
- Saved view `Revoke — result and source` restores in the repaired record.
- The repaired revocation shows `removed=true`, `grant_count=0`, `state=private`.
- The final recipient frame maps to original event
  `c982461aa06c4259a818ab17a4f5eaa3:999c6b5a37f442ccba0cad3282a20eaa:2551`.

Screenshots: [model confirmation](foundation-zh.png), [recording](recording-zh.png),
[data inspection](drill-data-zh.png),
[repair comparison](repair-en.png), [retest](verify-en.png).

## Acceptance

- [x] English and Chinese narrative form a continuous six-stage story.
- [x] Confirmation includes three real, independently inspectable model diagrams.
- [x] First build bridges confirmed models to the application and implementation.
- [x] Recording, stop, replay and seeking follow actual archived event identities.
- [x] Broad observation precedes progressive investigation and optional source.
- [x] Application captures follow forward and backward seeking.
- [x] A saved focused view is usable after the repair.
- [x] The same viewer stays mounted across chapters using the same recording.
- [x] 2D/3D, direct chapter links and locale switching work.
- [x] Browser checks and screenshots are saved, with fixes and retests recorded.
- [x] Original recorded facts and release archives remain unchanged.
