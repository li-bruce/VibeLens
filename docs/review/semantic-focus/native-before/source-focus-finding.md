# Source-panel finding: focus restoration reselects a node

Status: reproduced in the installed native b78f03a viewer; strict acceptance **failed**. Overall upgrade acceptance must wait for an upstream fix/new frozen version. This is separate from the passing business/Boolean/preset checks; the native rerender control is not a passing substitute for the original keyboard path.

## Minimal reproduction and strict test

From this project directory, run:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 review/framework-upgrade-b78f03a/keyboard_source_acceptance.py
```

The test restores the preserved native preference values, opens a fresh graph, focuses the previously unselected revoke semantic node, presses Shift+F10, and clicks Source. It performs no semantic rerender after selection and uses no alternate menu. It expects the actual panel to stay visible and contain `def revoke`. Current result: exit code 1, panel hidden and source not ready. The [result with passive focus/selection trace](keyboard-source-acceptance.json), [stderr](keyboard-source.stderr.txt), and [actual screenshot](browser-native/strict-keyboard-source.png) are preserved. Personal settings are restored afterward and observer controls add zero business events.

Both source responses are HTTP 200 with build `d8c853730fab2f69a76f2065201964f20292aa3b28de0edf604ac7911a35d023`. The [four-case source matrix](source-matrix.json) also records matching view, recording and source build identities, so the discarded old-recording response-label hypothesis does not explain this case.

The [controlled native UI probe](source-focus-probe.json) starts each case from the same saved preferences and performs only actual interface actions. Passive event/mutation listeners record DOM state; they do not replace handlers, inject business observations, prevent events or change framework code.

| Native sequence | Source response | Panel result |
|---|---|---|
| Focus a newly selected revoke node → Shift+F10 → Source | 200, matching build | Panel opens and then hides on focus restoration |
| Same selection → toggle native analysis details to rerender semantic controls → Shift+F10 → Source | 200, matching build | Panel remains visible and displays source |

In the failing trace, Source is clicked at 849.2 ms, the panel becomes visible at 860.5 ms, focus returns to the revoke node at 861.4 ms, and the panel is already hidden. In the rerendered control, focus returns at 851.8 ms while the panel stays visible. Timings are relative to each independent page and must not be compared as a latency benchmark.

Installed source explains the observed sequence:

- `static/graph/semantic-view.js:57`: the focus callback compares the render-time `selected` parameter with the node ID, rather than the class's subsequently updated selection.
- `static/graph/controls.js:83`: closing the menu restores focus to its return target.
- `static/graph/viewer.js:712`: selecting a node again clears `detailMode`; lines 718–719 hide the detail panel.

Yes: the trace, native source and controlled rerender support the render-time `selected` closure invoking `onSelect` again on menu focus restoration, which clears/hides the detail panel. `SemanticView.select()` updates `this.selected`, while the focus closure still reads the earlier render parameter. The strict trace also retains same-node aria-pressed mutations and panel visibility changes. The visible selection-actions menu returns focus to its own button and can display source, but neither that path nor the rerender control satisfies the failing keyboard requirement. This finding does not establish a transport/build mismatch, and no such mismatch was used to relax frontend validation.

These three files are byte-identical across this upgrade; the changed assets are only analysis.js and recording.js. No claim is made that b78f03a introduced the issue. The original failed attempts, actual response/build/source hashes and screenshots remain preserved. Personal preference values were restored via the native revision-checked API, and the probe produced zero business events.
