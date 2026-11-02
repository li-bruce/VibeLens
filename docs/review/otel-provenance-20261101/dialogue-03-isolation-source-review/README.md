# Trial 03 source isolation review

These are source-review findings captured before the trial's isolation repair.
They are not claims that a runtime counterexample had already been reproduced.

- `TeamFiles.provenance` formats observation-only metadata inside the native
  domain class without an observation prefix. The existing source-isolation
  contract requires a marked adapter helper.
- The queue's `carrier` column stores observation-only tracing data. It needs a
  `bo_` name or a separate metadata envelope, with existing queued data preserved
  by an explicit migration.
- The independent login reader calls `TeamFiles.principal`, which normally uses
  the observed storage path. Its own reads must use the independent read-only
  path; the repaired trial must test that native auditing emits no application
  events of its own.

The snapshots retain the code read during this review. Later runtime evidence
and acceptance belong to the trial's final review, not to this source finding.
