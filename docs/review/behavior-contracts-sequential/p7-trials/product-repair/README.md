# Prepared scene activity repair

Scope: P7-S02 in [the product findings](../product-findings.md). The local static
walkthrough now shares one activity predicate between SVG and WebGL renderers.
Node identity takes precedence. State values additionally require matching model
identity whenever either side is qualified. Legacy single-model scenes retain
their original unqualified behavior.

The first regression failed because a `grant:active` event also activated
`session:active`: [failure](activity-before.log). The same test passes after the
fix: [retest](activity-after.log). It also covers missing model ownership,
different explicit identities, direct activity, empty input and legacy behavior.

The original product data suite passes with this additional check:
[regression](product-regression.log). Its archived source, recording, transition,
transfer and first/last confirmation expectations are unchanged. The new check
is included in `test_product_demo.mjs`, so the existing full runner executes it.

This is a targeted rendering repair. The new multi-model story and final browser
batch remain pending; this receipt does not complete A26 or P7. It changes no
installed provider, native application, protected field or runtime recording.
