# Remark iteration: independent evidence review

The original `remark-v2-independent-01` files are preserved. Its 24 pending
items largely came from default filenames that this trial did not use. The
actual strict receipts are under `review/remark-v2/results`; the browser's
single results file contains both live and replay checks. It names the real
saved recording rather than copying it beside the browser results.

The second audit selects these actual receipts explicitly. The only schema
adaptations are the combined recording identity, its actual storage location,
the existing `viewer_controls_no_business_events` check and explicit absence of
`.gitignore` when the accepted advisory input is also absent. It compares the
review verification copy with the authoritative phase verification. None of
the identity, source-hash, receipt-digest or category requirements were removed.

The accepted candidate is `92b40c1d8568e710cb2cc52fb304ad4987ebcf180b0da97e1ba3a490ec9a90bc`.
Its build is `3a07278154d5ac21a4341161c26c78d3ff285d6c50cdca21ff04024e3212207c`.
All 49 manifest inputs and 36 accepted inventory source files match current
bytes. Mapping, state rules, project checks and business assertions passed
separately; all 126 authored business assertions executed. The browser reports
28 true checks, with the actual accepted-build recording containing 1,364 events,
six runtime frames and no gaps. All 116 earlier graph identities remain; the
41 main and 26 business-view saved positions remain unchanged.

Two strict global-revision flags remain in audit 02. API and documentation
receipts refer to `366a9563...`, matching native verification and the recording.
The current saved code graph uses `96ba286d...`. Direct comparison finds exactly
one changed filesystem fact: `manifest.json`. Its parsed value is unchanged.
Expanding the current file's 6,457 LF characters to CRLF **in memory** exactly
reproduces the recorded earlier SHA-256 and byte size. The eight physical API
endpoint nodes are identical between the recording and current code graph.

This proves the revision difference comes from manifest line endings, with no
observed source, route, model or build change. The strict raw-byte/global-revision
flags remain visible; this audit did not regenerate receipts or replace their
claimed revisions. The detailed proof is in
[remark-v2-independent-02-revision-proof.json](remark-v2-independent-02-revision-proof.json).

Human review still covers the actual graph/timeline screenshots, projected state
intervals, whether remark privacy matches the confirmed intent and intentional
changes to view filters. The audit made no application imports, requests, native
verification calls, project writes or recording edits.
