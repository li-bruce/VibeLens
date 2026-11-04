# Trial evidence audit

Phase: `remark-v2`. Status: `needs_review`.

This reads existing source hashes and receipts; it does not run the application or certify user intent.

Native categories:
- mapping: passed
- state_rules: passed
- project_checks: passed
- business: passed

Pending or inconsistent evidence:
- Missing evidence: review/remark-v2/final-current-check.json
- Missing evidence: review/remark-v2/source-docs.json
- Missing evidence: review/remark-v2/api-observation.json
- Missing evidence: review/remark-v2/browser/replay-results.json
- Missing evidence: review/remark-v2/browser/recording.json
- Mismatched evidence: current_receipt_present
- Mismatched evidence: docs_receipt_present
- Mismatched evidence: api_receipt_present
- Mismatched evidence: replay_receipt_present
- Unproven check: advisory_input:.gitignore
- Unproven check: current_receipt_valid
- Unproven check: native_current_status
- Unproven check: docs_source_revision
- Unproven check: docs_receipt_valid
- Unproven check: api_source_revision
- Unproven check: api_receipt_valid
- Unproven check: api_complete
- Unproven check: replay_receipt_checks
- Unproven check: browser_recording_build
- Unproven check: browser_recording_identity
- Unproven check: replay_recording_identity
- Unproven check: replay_recording_build
- Unproven check: recording_no_gaps
- Unproven check: browser_observer_exclusion_receipt

Human review:
- Current candidate ID is linked through retained native receipts, not independently recomputed by executing project tools.
- Event counts cover direct raw IDs; projected state residence/API periods need browser review.
- HTTP numbers are observed outputs; semantic expectations remain in the separate business assertions.
- Observer exclusion detection covers identifiable runtime sources plus the browser receipt, not arbitrary unknown instrumentation.
- Review changed layout positions, all intended layers and remark privacy through the actual browser screenshots; old or identity-unbound browser receipts are not fresh execution proof.
