# Single-rule focused capture loses the real invocation boundary

Classification: shared capture/recording limitation. No project business workaround or managed-source edit was made. The coordinating conversation requested a freeze and canonical maintenance. A later direct user answer permits truthful missing-ownership disclosure in a partial recording; that answer does not make the missing relation complete and does not revoke the freeze.

## Actual reproduction

1. Start the existing development launcher after the normal canonical upgrade.
2. In Web, choose the permissions view, select only `policy:actor_is_recipient`, choose focused capture and start recording.
3. Use the real logged-in synthetic `cara` session to download the previously approved and shared file. The real HTTP download returned 200 with the expected 101 bytes.
4. Stop using Web and inspect the saved recording and Timeline. Capture is restored after stop.

Raw evidence: `focused-recording.json`, `raw-recording-cee869d25e1e46b7ba252e8e00516b5f.json`, `focused-start.json`, `focused-timeline.json`, `focused-single-rule.png` and `focused-dom.html`.

The requested root is exactly `policy:actor_is_recipient`. The resolved scope is that node plus the static `policy:network` boundary. The business parent and `http_request` are outside it.

The single real decision retains file entity/attempt `a1105ad783834dfeadc71b99310803e4`. Its `parent_call_id` is `56533c107f394a6fb56a65f5e62b8f14`, while `parent_event_id` is null. Neither recording context nor captured events contains the corresponding invocation entry. Time, file identity and static ancestry cannot recover that entry. Timeline has zero invocation groups and one unassigned observation. It visibly labels the row `Unassigned observations` / `归属待确认`, gives the point no function duration and does not fabricate a business execution.

There is also an explicit, independent pre-recording-context retention note because the live stream had exceeded 2,000 events. The missing parent here belongs to a new operation after focused recording began; it was excluded by scope, rather than a pre-recording entry that could be restored by increasing old-history retention.

## What passes separately

- Full recording `d4bf7718e7e6474aa816e65583cdf3f6`: 3,265 real events, no gaps, 103 actual HTTP roots, 1,641 checked internal point facts. All resolve to actual HTTP invocation entries with preserved explicit file identities.
- Normal gate: all four reports pass and strict invocation closure checks 591 calls. Complete-run closure does not prove focused-recording ownership.
- `builder-audit.json`: a real Flask request using the canonical probe and existing integration methods executed exactly one selected rule builder; unselected field builders executed zero times. This is explicitly a direct-sink test, separate from Web/collector validation.
- `focused-capture-result.json` and `focused-restoration-live.json`: stop restored complete capture; another actual download produced normal HTTP/business/data/rule observations, pending queue zero and capture/data/integration errors zero.

## Canonical maintenance boundary

A potential canonical repair would preserve minimal real invocation identity and causal boundaries without evaluating excluded business field builders. It must not infer missing historical references, widen selected business fields, rewrite recordings, or declare internal predicates as external roots. Preserve the current truthful unassigned diagnostic for genuinely unavailable evidence. Add single-rule, cross-entity, concurrent, queue/drain and restored-scope regressions before claiming complete focused causal mapping.

The trial is frozen. No such repair is authorized inside this project.
