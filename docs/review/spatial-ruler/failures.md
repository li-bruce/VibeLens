# Failure and repair log

- Initial geometry regression used strict plane equality at Y=260. Cubic interpolation exposed floating-point Y drift. The path now explicitly retains the semantic plane; original assertion passes unchanged.
- `browser-first` and `browser-port-diagnostic` failed the circular-port assertion in orthogonal mode. Saved positions include `pinned`; generic interpolation incorrectly included metadata in distance calculations, yielding a wrong source port. Restricting interpolation to x/y/z fixes it. `test_ruler_controls` now uses pinned coordinate objects; `browser-port-retest` passes the original port assertion for all four shapes.
- Earlier `replay-first` and `replay-controls-first` receipts separately cover unchanged state-fact presentation and new playback controls. They remain pre-final receipts.

Raw recordings and native business/runtime source are unchanged. No expectations were removed to obtain a pass.

- `checks-before-final-pointer-review` retained an old browser helper that enumerated every ruler button as a visibility toggle. The new reorder/name buttons have no `data-layer`, so it tried to click `data-layer=undefined`. Narrowing the helper to actual eye buttons retains the visibility assertions.
- `checks-pointer-harness-failure` read screen coordinates before the throttled geometry update and submitted NaN to Chrome. `checks-offscreen-pointer-failure` then clicked an offscreen state left by a previous saved 2D camera. The final harness waits for finite coordinates and uses the existing F-to-locate control before clicking actual geometry. Its Delete and focus assertions remain.
- Pointer handlers now explicitly focus the graph after a canvas pick, so Delete works after editing a text field. 3D edge picking uses projected segments and takes precedence over empty region fills; group dragging remains covered. Preliminary example review receipts are kept separately; final review was rerun after these source changes.

- `checks-before-badge-fix/test_spatial_performance` exposed a renderer assumption: the benchmark's flat scene omits child metadata, and the new badge tried to read `kids.length`. The component now leaves an absent child count unknown, retains actual counts from complete graph boxes, and has a direct missing-metadata regression. The benchmark fixture and its performance assertions were retained. Strict example review/verify are rerun after this source repair.
