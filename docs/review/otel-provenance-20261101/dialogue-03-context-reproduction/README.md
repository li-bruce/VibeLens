# Context selection cannot distinguish two native review calls

The same complete case executes two actual HTTP reviews of one file. The uploader's own review is denied; the other administrator's review succeeds. Native Flask sessions and SQLite rows independently establish the two principals. Direct SDK SpanContexts identify their actual invocations. Every original event, including full API ancestors, is retained.

Both public context rows select case=two_reviewers, node=review_file, phase=enter. Each row is applied to both events, so two correct native observations produce two mismatches. Adding another row cannot express which native invocation belongs to which event.

Required binding: retain one complete case, select an event by a native invocation key such as trace_id plus span_id, and compare it to the matching independent native fact. The two exact joins in report.json are diagnostic evidence, not replacement validators or acceptance.

The original protected mapping.json, initial baseline and strict complete-run check are unchanged by this reproduction.
