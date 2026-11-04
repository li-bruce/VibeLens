# Execution-band browser routing check

The v0.12.1 tag run failed while checking 2D orthogonal endpoint geometry. The
failure is a browser-test sampling race. No change to the published Skill or its
viewer assets was required.

## Preserved failure

- Run: `41880303713`, job: `126750700052`.
- Original log: [remote-tag-browser-failure.log](remote-tag-browser-failure.log).
- Original artifact: [remote-tag-browser-artifact.zip](remote-tag-browser-artifact.zip),
  GitHub artifact `13348668025`, 7,216,126 bytes.
- SHA-256: `5343164a24041086f31f8cb00edfb08e3539a772193c7f890494c31eb539303d`.
- Extracted [failure result](execution-routing-before/result.json) and
  [screenshot](execution-routing-before/failure.png).

The assertion sampled zero matching icon anchors. Its later failure capture
contains seven rendered orthogonal paths and seven matching presentation edges,
with no browser errors. The same product bytes also passed the main-branch job
`126751187906`. These observations support a timing defect in the acceptance
script; they do not establish a persistent missing-edge defect in the product.

## Cause and correction

`test_execution_bands_browser.mjs` previously waited for render readiness, then
read paths and endpoint positions in a second browser evaluation. A queued
reroute can begin between those two evaluations. Orthogonal and bus routes clear
the preceding geometry while their worker computes replacement paths.

The test now lets the routing control's scheduled render run, then reads
readiness, paths, presentation identities and icon coordinates in one browser
turn. It saves that exact sample before checking it. The two original
requirements remain unchanged: at least one real icon anchor and every measured
endpoint error below `1e-5`. The test does not accept a blank sample, rewrite
geometry, call private renderer actions, or reduce endpoint precision.

## Retest

Both tests used installed Chrome, the real isolated concurrent-worker fixture,
real SQLite writes and pointer/keyboard controls. No trial-chat application was
accessed.

| Recording boundary | Events | Execution bands / rows | Routing checks | Result |
| --- | ---: | ---: | --- | --- |
| Before work starts | 33 | 2 / 8 | 2D and 3D, straight/curve/orthogonal/bus | Passed |
| During active calls | 15 | 2 / 8 | 2D and 3D, straight/curve/orthogonal/bus | Passed |

Every routing sample contains 13 actual icon anchors. All 2D errors are zero;
the maximum 3D error is `2.2737367544323206e-13`. Both runs retain the original
six checks, zero browser errors, actual business results and unchanged recorded
events after viewer interactions.

Evidence: [normal recording](execution-routing-normal-after/result.json),
[mid-span recording](execution-routing-midspan-after/result.json). Each directory
also contains eight `routing-{mode}-{style}.json` snapshots and actual screenshots.

Only the browser test and review evidence changed. Product source, managed
copies, versions and release archives remain unchanged.
