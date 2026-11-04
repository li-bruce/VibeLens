# Managed example integration

## Final accepted candidate

Both examples completed the full native workflow again after the exact HTTP
observation mapping and legacy focus-selection fixes. The final frozen record
is `graph-quality-20261104-api-focus`. All canonical runtime files, language
adapters and viewer assets match the approved source; the managed upgrade plan
has no pending changes, conflicts or retired files.

| Example | Final candidate | Configured project tests | Result |
| --- | --- | --- | --- |
| Delivery | `e686ebc92a023fa8fc68e5bc6a34c0915f4c3b9ef2b47938ef1c6b863981593c` | 9 | Passed |
| Team archive | `55b0a42a5f386f1ec422524526ac11e6151d3bf344b3c71756e7bda9efbb6afd` | 5 | Passed |

- [Delivery final acceptance](examples-delivery-api-focus-final-acceptance-summary.json)
- [Archive final acceptance](examples-team-archive-api-focus-final-acceptance-summary.json)

Generation, sealing, scanning, explicit review, verification, acceptance and
current-input checks passed. Both original baseline hashes below remain
unchanged. Mapping, state rules, business expectations and project checks are
reported separately. Existing business source and acceptance expectations were
preserved throughout the runtime updates.

## Separate legacy source diagnostics

The non-strict source documentation reports list 57 missing comment items for
delivery and 166 for team archive, with no scanner errors. These are explicit
legacy documentation gaps; the report does not certify source documentation as
complete or impose a new strict documentation requirement on unchanged business
code.

The examples have no configured HTTP collection contract. Their `api-check`
reports therefore return `configured: false` and `not_applicable`; these reports
do not demonstrate HTTP runtime capture. The dedicated exact-route backend,
frontend and browser regressions supply that evidence separately.

- [Delivery source comments](examples-delivery-final-source-comments.log)
- [Archive source comments](examples-archive-final-source-comments.log)
- [Delivery HTTP scope](examples-delivery-final-http-coverage.log)
- [Archive HTTP scope](examples-archive-final-http-coverage.log)

## Earlier accepted caption phase

Both maintained examples completed the normal generation, ownership sealing,
source scan, explicit review, verification, acceptance and current-input checks.
Its frozen release record is `graph-quality-20261104`. Earlier records remain.
This passed native phase precedes the separately identified API runtime-source
projection correction. The final candidate above repeated the same normal
workflow on the original baseline.

| Example | Final candidate | Configured project tests | Result |
| --- | --- | --- | --- |
| Delivery | `8b3db0b1a5140fd32bc8ef944855d4b91add9b027926ea230cc07a810f097f0e` | 9 | Passed |
| Team archive | `1abe57a04701d7b6b9071d3fc00eded16a25b254b4962515bf905f2ef472636d` | 5 | Passed |

Verification records report mapping, state rules, business expectations and
project checks separately. The final summaries retain every executed command,
return code and raw log reference:

- [Delivery final acceptance](examples-delivery-caption-final-acceptance-summary.json)
- [Archive final acceptance](examples-team-archive-caption-final-acceptance-summary.json)

## Preserved baselines and guards

The original change baselines were continued throughout the repair:

- Delivery SHA-256: `4b95f3fbf81c20f02e52e3fd8876016e13c41b08fa389502407129c94e530b73`
- Archive SHA-256: `8f786ba384a5d2ddd4b005158cd6fa94871aa4244a27c1d10b370791f669c7e4`

[Vendor approval](example-vendor-approval.json) checks unchanged business source,
state declarations, intent, mapping and independent expectations against those
baselines. Only the three exact `routing-tools.vendor.js` pins were approved,
from `9ddfbf...8747` to `83f6ae...f599`. The dependency remains D3 hierarchy 3.1.2
under ISC; its existing `packEnclose` export was added to the reviewed bundle.

Architecture sealing first rejected both examples with `changed_vendor_file`:
[delivery](examples-delivery-seal-before.json),
[archive](examples-archive-seal-before.json). The exact guard remains active.
Approved pins, regenerated managed hashes and both seal retests passed.

## Failures and follow-up candidates

The full gate caught the existing planar label-containment assertion. The fix
encloses the actual visible label rectangles as well as glyphs, without adding
hidden owner coordinates. The unchanged
[layout regression passed](examples-delivery-layout-label-retest.json).

The first archive review writer stopped on an unrecognized existing observation
adapter. [The retained failure](example-first-candidate-harness-failure.json)
records its explicit source review; business classifications were not changed.

Delivery's first native candidate passed before subsequent browser findings
required caption and source-scanner follow-ups. Its acceptance is preserved as
`graph-quality-20261104-first-candidate`; publication was held and recorded in
[the hold report](example-release-hold.json). The final candidate was regenerated
and fully verified on the same baseline after the renderer and parser froze.

Final managed upgrades copied the latest adapter and viewer through the normal
`bo_upgrade.py plan/apply` workflow. Freezing required explicit `--freeze`, all
normal native checks, unchanged baseline hashes, and byte equality between the
copied viewer and canonical viewer assets. No pending hold marker remains.

The reproducible [acceptance runner](finish_example_acceptance.py) keeps each
pass's evidence under a unique label. Whole-repository gates, clean Git export
checks and actual browser acceptance are recorded separately in this review.

The first API-runtime archive candidate passed all native stages, but freezing
correctly refused a canonical viewer asset that changed afterward. The
[freeze-guard record](example-api-runtime-freeze-guard.json) preserves this
failure. Final acceptance was rerun under the distinct `api-focus-final` label
after the source froze; earlier accepted candidates were retained.
