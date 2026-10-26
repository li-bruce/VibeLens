# Failures, repairs and retests

## Deliberate business failure, retained

V1's requirement is to publish only the version the reviewer opened. The actual browser sequence gives the policy `reviewed_version=1` and `current_version=2`. Its return is `allowed`; the actual version-selection transformation and database write use 2. The independent expectation is `stale_review`, so the business result remains red in the exported receipt.

V2 adds the comparison in `policy.py`. The same stale request returns `stale_review` and the exhibition remains empty. Reopening version 2 allows the transaction to publish 2. Both builds pass source/data mapping checks; that does not erase v1's business failure.

## Implementation issues found while building the case

| Failure | Cause | Repair and retest |
|---|---|---|
| `multi-target writes require explicit target_actions` | Initial data operation declaration omitted per-table access roles | Added exact read/write roles for artwork, image, message and exhibition targets; canonical data projection and runtime checks pass |
| `missing intent`, missing explanation/provenance | Initial fixture did not satisfy the existing strict model contract | Added confirmed intent, bound explanations and edge provenance; no contract was relaxed |
| `'events' is not of type 'object'` | Adapter sink arguments were reversed | Corrected `(event, kind)` callback; both real runs have zero ingestion errors |
| `64 !== 63` in observer-exclusion assertion | The browser's legitimate PNG request was still finishing | Wait for the displayed image to decode before testing observer-only requests; repeated runs keep zero observer events |
| Empty permission view | Example nodes lacked explicit permission roles | Added semantic roles; all eight filtered views now have nodes and relations |
| 3D action changed the selected analysis | Parent page rerender reapplied the chapter's preset | Dimension controls now change only the mode; both renderers retain the user's view |
| Mobile horizontal overflow | Long source code determined a grid child's minimum width | Added explicit minimum-width behavior; 390px EN/ZH checks pass |
| Native event revalidation rejected `source_seq`/`stream_id` | Validator received collector annotations instead of the native envelope | Validate original producer sequence after removing only documented collector annotations; keep stored evidence unchanged |
| Recorded case appeared as “Live observation” | Unmodified viewer label was misleading for a static host | Label the captured final state explicitly; hide unavailable capture controls and keep actual replay |
| A layer selection immediately after switching builds was lost online | The iframe had rendered before its ready message reached the parent; controls discarded requests during loading | Queue the latest requested view, mode and expansion; reject ready messages from an obsolete build or language. A delayed-network browser regression now exercises the early selection |

Final runs: [runtime](receipts/runtime.json) and [browser](receipts/browser.json). The original illustrative exercise is retained and tested separately. Frozen release evidence and canonical renderer files were not edited.
