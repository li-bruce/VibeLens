# Failures, repairs and verification boundaries

Raw earlier files are in `preliminary-evidence.zip`; its manifest records their original relative paths and SHA-256 hashes. Successful preliminary runs are not relabeled as final acceptance.

| Observed failure | Repair | Final evidence |
|---|---|---|
| Node's libavoid loader aborted, including after correcting an encoded Windows path. | Production uses the tested browser module worker. The Node loader is not presented as validated. | Actual browser Wasm route in `final-checks/test_routing_browser/results.json`. |
| Global libavoid routing of 100 shapes / 400 links took about 10 s; the larger prototype exceeded its deadline. | R-tree candidate checks and bounded local solves replace a global connector solve. | Browser engine receipt and performance results. |
| Local per-edge solves exceeded 120 s before completing 4,000 nodes / 16,000 edges. | Reusable Delaunay channels, ngraph path search and cached plane-pair indices. | `performance-accepted/results.json`. |
| Early channel routes and unconstrained spline sampling crashed the browser under the 4,000-node load. | Remove collinear points, use certified shortcut samples, bound smoothing, transmit route deltas, dispose the previous benchmark renderer before the next case, and upload a completed large edge buffer once. | Final large graph, real pointer drag and idle camera test passed without crash. |
| Exact path search and repeated full collision collection still exceeded the 120 s route deadline. | Bidirectional greedy A* for visual routes, reusable path caches, bounded shortcut candidates and early-exit boolean collision checks. | All 16,000 routes completed; first routing about 17.8 s on the named host. No global optimality claim. |
| An open icon's empty center was not picked by triangle raycasting; a real node drag failed. | Add a full circular interaction target on the same semantic plane. | Final layered drag and 4,000-node pointer test. |
| The test still used the ruler button to open spacing after that button became the compact toggle. | Exercise compact width, hidden full labels, retained eye controls and the separate spacing button. | Final layered browser test. |
| Tests imported the old glyph-shape API after the primitive shapes were replaced. | Retain the API with shared vector strokes and rerun code/data view checks. | Final code-view and database-view groups. |
| The new minified utility bundle triggered `Ambiguous source identity: n` during architecture validation. | Register only the exact reviewed vendor hashes in both examples. The parser, business source coverage and managed-file checks remain strict. | Both strict examples and the deliberate changed-vendor rejection. |
| The prototype asset server attempted to send a second status after a missing favicon. | Read the asset before sending response headers. | Final browser engine harness. |
| A staged-byte audit found that the archive example's nested `* text` rule normalized the new Wasm binary. | Add a local binary exception and restage the original bytes. | `git-byte-proof.json` compares staged assets and frozen evidence with the tested working files. |

The new native dependencies are shipped as separately replaceable files with licenses and pinned source material. A byte-identical libavoid rebuild has not been demonstrated. Original business/native source hashes and immutable example baselines are preserved. Final checks verify implemented mapping and runtime behavior within their stated cases; they do not prove semantic completeness of arbitrary applications.
