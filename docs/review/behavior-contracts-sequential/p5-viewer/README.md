# P5 — Progressive inspection

This phase extends the existing graph details and recording context. It does not
start an independent dialogue trial. P7 retains that acceptance responsibility.

## Failure and repair record

| Attempt | Observed failure | Repair and retest |
|---|---|---|
| `details-before.log` | Detail projector absent | Added one definition index shared by both renderers |
| `action-path-before.log`, `trace-first.log` | A business action was not reached through its declared state event | Follow the actual `action_requests_event` and `requests_transition` relations |
| `recorded-details-before.log` | Recording checkpoint omitted the definition context | Retain detached context at recording start, not on every frame |
| `details-first.log` | Windows sandbox temporary-directory cleanup denied | Rerun in workspace `.validation`, without changing assertions |
| `backend-regression-first.log` | Node real-path access denied; one runner module name was wrong | Use the existing Python model-network test and host process permission |
| `browser-first.log`, `test_timeline_performance.log` | Playwright's bundled browser was absent | Use installed Chrome through the existing executable override |
| `browser-chrome/result.json` | Harness closed details already retained from the previous mode | Click the disclosure only when closed; `browser-retest/result.json` passes |
| `locale-before.log` | Screenshot review found untranslated Action and Binding labels in Chinese | Add the missing messages; `locale-retest.log` and `browser-release/result.json` pass |
| Example metadata review | P4-only helper rejected newly regenerated viewer files | Compare each changed viewer file byte-for-byte with its canonical source before allowing it; preserve all original verification gates |

## Tests

`backend-final.log` contains 76 passed tests. Frontend suite logs cover detail
rendering, logical trace separation, retained views, actual lifetime indexing,
recording replay, typed projections and scoped controls. Browser artifacts include
English/Chinese 2D/3D details and actual native multi-model recording, Timeline,
catalog refresh and restored per-network views.

`browser-release/result.json` is the final detail/highlight browser run. Earlier
screenshots remain as historical evidence, including the untranslated labels.

`timeline-performance/result.json` is a synthetic component benchmark on this
host: 20,000 events, 9,999 causal links, first index/paint 175.5 ms, seek P95
23.1 ms, paint P95 19.2 ms. It excludes whole-graph reconstruction and is not a
business-correctness claim.

Final phase status is recorded in `results.json` after regression and clean-export
checks. Earlier failed attempts and screenshots remain alongside the passing run.
