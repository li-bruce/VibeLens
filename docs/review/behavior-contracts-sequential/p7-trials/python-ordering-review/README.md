# Python trial: verify actual execution order

P7 remains in progress. The first repair-23 ordinary recording failed after four
of twenty assertions. Its script saw a queued task, clicked revoke, then expected
rejection. The native journal shows request 119, admission 120, completion 121,
and revocation 122 for that same task and grant. Ready is the correct outcome for
the confirmed policy. The test did not establish its required ordering.

The [original analysis](failure-handoff/REPORT.md) joins native transactions,
policy facts and exact state frames. All 1580 events in this executed prefix were
retained, six commits and six reads have matching frames, and ordinary Stop
settled target/completed/submitted 1760 with zero pending, drops, errors or retries.
These are prefix capture results; the full scenario remains failed/incomplete.

The [test construction review](failure-handoff/TEST_CONSTRUCTION_REVIEW.md) keeps
all original assertions and distinguishes controlled ordering from the default
worker. A separate deterministic case must retain the denied input/pre-state
context check. A normal run derives its expected outcome from independent native
ordering and the confirmed rule. An absent branch is unexercised in that record.
Each original assertion needs an explicit evidence location; no retry-until-pass,
longer deadline, production scheduling change or weaker expected value is allowed.

The Skill's iteration-check reference now states this distinction. Runtime code,
business definitions and capture budgets are unchanged. The next fresh Skill
installation and actual retests will supply their own receipts; this review does
not mark those pending checks as passed. Original artifacts are copied byte for
byte and indexed in [provenance](provenance.json).
