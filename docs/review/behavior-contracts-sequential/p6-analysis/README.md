# P6 — Optional finite design analysis

Implementation and regression are complete. No independent conversation trial
has started; P7 follows only after this phase's full regression and clean export.

The full runner reported 1,090 unittest records across 95 suites: 1,089 executed
and one host skip. Windows denied the file-symlink privilege (WinError 1314);
`host-symlink.log` preserves the isolated retry. Directory-junction guards retain
their existing executed coverage. This skip is not counted as an executed pass.

## Failure, repair and retest

| Evidence | Observed issue | Repair |
|---|---|---|
| `collections-before.log` → `collections-retest.log` | Collection domains could not become typed conceptual facts | Shared recursive fact/capture types; explicit queue/set operators |
| Initial local TLC probe | Java output used the Windows code page | Fixed UTF-8 and locale flags; retain raw process files |
| `tlc-first.log` → `tlc-second.log` | Fairness test omitted required rationale/invalidation fields | Correct the fixture; keep strict assumption validation |
| `tlc-fourth.log` → `tlc-fifth.log` | Initial invariant failure carried its state inside message 2107 | Decode that actual state instead of losing the counterexample |
| `source-first.log` | Duplicate Chinese message key | Reuse the existing initial-state translation |
| `browser-first/zh-CN-3D.png` → `browser-release/result.json` | Numeric renderer color was invalid SVG CSS; Values lacked translation | Convert shared layer colors to CSS and add the missing label |

| `native-first/result.json` → `native-third/result.json` | Reproduction harness used an obsolete view ID, then counted a replay prefix as the whole recording | Select the actual functions preset and compare immutable saved recording bytes; retain both harness failures |

## Independent expectations

The handwritten `tests/fixtures/tlc-oracles/` model has four physical states.
Actual checks test reachability of each combination through negated invariants.
The generated model retains action metadata, resulting in seventeen TLC states;
this is reported separately rather than treated as seventeen business states.

Real tool cases cover invariants and after-state constraints; queue overflow and
analysis bounds; typed finite holder sets; canonical shared Boolean decisions;
weak/strong fairness and a non-stuttering loop; per-property assumption isolation;
deadlock and declared termination; empty initial sets; cancellation, timeout and
missing tools; artifact edits and source/model drift. Native reproduction is an
independent plain-function fixture and is not claimed to prove arbitrary code
equivalence. Unsupported protocol/engine semantics stay unsupported.

Browser evidence uses actual TLC output, a real design server, English/Chinese,
2D/3D, original node selection and logical-step dragging. The runtime event list
remains empty. Broader native recording and iteration checks remain in the normal
full regression and P7 trials.

The separate native reproduction uses the real SQLite application fixture and managed producer. Its independently read states match the actual TLC counterexample. The same page displays five captured events and real call duration, then imports logical steps in 2D/3D without changing the saved runtime recording. This focused UI fixture does not claim full application binding acceptance.

Raw TLC attempts are in `tlc-attempts.zip`; `tlc-attempts-index.json` records every member checksum. Original unpacked attempts remain locally.

Candidate-bound counts, files and checks are recorded in `results.json` after full verification and clean export. Earlier failed attempts remain retained.
