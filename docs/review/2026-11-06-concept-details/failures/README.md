# Failures, corrections and retests

Original logs and screenshots are retained rather than overwritten with a pass.

| Observation | Cause | Correction and final check |
| --- | --- | --- |
| Candidate changed during the first acceptance | Maintained files were formatted while the candidate checks were running | The existing gate rejected the changed candidate. Subsequent acceptance used frozen source; no baseline or validator was weakened |
| Browser could not launch | The sandbox's Playwright browser download was absent | Use the installed Chrome executable explicitly |
| Real AI call failed inside the restricted Windows environment | Temporary-directory access was denied | Run the read-only integration test under normal desktop permissions; the installed Codex login produced a real answer |
| Directory-junction regression failed in the restricted run | Windows refused the test fixture's junction creation | Rerun the unchanged test in the final complete gate with normal permissions |
| AI job completed but the answer was below the panel's scroll position | The explanation appeared after a long definition | Move it directly under the heading, reveal it on completion, and assert its actual visible bounds |
| Business “Next” included implementation helpers | Generic native call edges also used `flow` | Select business-plane neighbors and, for confirmed concepts, declared conceptual edges |
| The 3D orbit test did not move the camera | Fixed screen coordinates hit a region or the expanded legend | Frame the graph, choose the left canvas margin, verify the actual hit target and assert that orbit leaves node coordinates unchanged |
| Nested states could omit inherited transitions in details | The detail list matched only the immediate state | Reuse the existing hierarchy parser to include ancestor transitions |
| A state-model group displayed `phase = undefined` | The canvas treated every state-plane node as a concrete state value | Keep the group's definition summary and actual binding feedback; do not render an absent value |
| Two first-use requests could initialize separate AI registries | Lazy provider setup was outside the job registry's lock | Serialize initial setup; concurrent-tab regression verifies one shared registry |

`answer-below-fold.json` and `business-neighbors.json` show why successful DOM/job assertions alone were insufficient. The accompanying screenshots exposed the display and semantic defects; the final browser tests add explicit checks for both.

`full-gate-interrupted.log` is an interrupted development run, not final acceptance. Complete acceptance is recorded in the parent review's final evidence.
