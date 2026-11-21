# Read-only observation flow diagnosis

Native producer finite waiting queue overflow: dropped 421, stage queue / type Full. Later flush completed; lost envelopes remain lost and the second recording is interrupted.

| Existing sample | UTC | Enqueued | Pending | Completed | Dropped | Retries |
|---|---|---:|---:|---:|---:|---:|
| after-start-1a56737f20d34900bbecd418eb18836b | 2026-11-21T20:06:52.875738+00:00 | 2423 | 0 | 2431 | 0 | 0 |
| before-stop-1a56737f20d34900bbecd418eb18836b | 2026-11-21T20:06:56.599578+00:00 | 11799 | 8256 | 3162 | 421 | 0 |
| before-stop-1a56737f20d34900bbecd418eb18836b | 2026-11-21T20:07:26.044204+00:00 | 11799 | 0 | 11418 | 421 | 1 |

The native waiting limit remains 8192, with at most 64 in flight (observed pending 8256). Original batches remain at most 64 events / 256 KiB, per-envelope 24 KiB, one serial group, 1000 ms request deadline and two attempts. Snapshots retain their separate ordered barriers. No limit, field, timeout or retry policy changed.

Over the captured 3.701s burst interval, the enqueued counter rose 9376 and completed envelopes rose 731. The remaining 8256 pending envelopes drained over 29.468s, approximately 280.2 completed envelopes/s. Those are sample-window counters, not measured HTTP request latency.

The unprofiled original run has producer health polls, stop-request elapsed times, aggregate system CPU and original event observed_at values. Viewer stdout/stderr contain no ingress request timing/access records. No packet-level batch-size or collector-request duration trace was collected. Do not substitute stop elapsed time or backlog-drain time for event-batch server latency.

Candidate measurement locations are the unchanged SDK serial batching/request path, the collector HTTP batch route, and the atomic event_batch reducer (per-event validation, both source binding checks, detached cursor copies and locked publication). Their individual costs are not established by this run. `flow-bottleneck-diagnosis.json` preserves source hashes/copies, exact counters, node distribution, limitations and source references; `flow-health-timeline.json` preserves all 214 original sample points. Original raw run files are unchanged. No business rerun or new profiler was used.
