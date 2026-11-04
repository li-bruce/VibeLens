# Managed example integration

## v0.11.2 reserved output boundary acceptance

Both examples use the managed 0.11.2 runtime and viewer copies. Source discovery
and the filesystem graph now share the reserved output boundaries for
`bo_stategraph/config` and `bo_stategraph/data`. An explicitly owned source
subtree can still be included. The existing literal artifact declarations,
business/state code, probes, original baselines and every test expectation were
retained. Watched configuration files keep their byte-integrity checks.

The complete generate, seal, scan, inspect, verify, accept and check workflow
passed. Each example then passed an additional current-input check after the
new record was frozen as `graph-quality-20261104-reserved-boundaries-0112`.

| Example | Final candidate | Configured project tests | Result |
| --- | --- | --- | --- |
| Delivery | `989172c07cd2004ffd06c39fce9c6d6011138c1905e0d0281d0b1a9a3a8d08ea` | 9 | Passed |
| Team archive | `5dc99b8fb5bf534e2a15ab53fb6e4e317070fa05d9bac47681a9e84fd911f46f` | 5 | Passed |

- [Delivery acceptance](examples-delivery-reserved-boundaries-0112-final-acceptance-summary.json)
- [Archive acceptance](examples-team-archive-reserved-boundaries-0112-final-acceptance-summary.json)
- [Delivery post-freeze check](examples-delivery-reserved-boundaries-0112-post-freeze-check.json)
- [Archive post-freeze check](examples-archive-reserved-boundaries-0112-post-freeze-check.json)

The initial stale-review refusals remain in the before-review reports. Both
final inspections and all verification stages passed after explicit review of
unchanged source. No baseline, source requirement or check was relaxed.

The [staged-input comparison](example-reserved-boundaries-0112-staged-parity-02.json)
checks all 682 accepted model, intent, managed-runtime, watched-file and scope
inputs against exact Git blob bytes. The first comparison covered 680 inputs;
the repeatable helper now also includes both root intent files. Both reports
are retained. The [clean Git export](clean-staged-export-reserved-boundaries-0112-report.json)
passed both unchanged native current checks from the frozen receipts; its
[command receipt](clean-staged-export-reserved-boundaries-0112.json) records exit 0.
Both `.gitignore` files retain the accepted 194-byte LF form; the
historical `whitebox-v04/review.json` index blob remains equal to Git HEAD.
Earlier frozen records and failed clean-export evidence remain intact.

## v0.11.1 portable source-scope acceptance

The clean Git export rejected the earlier source-scope approvals because both
local `.gitignore` files used CRLF while the existing Git blobs used LF. These
files now contain the exact existing 194-byte Git blobs; their ignore rules are
unchanged. No framework source, hash guard, original baseline, business/state
code or test expectation was changed for this correction.

Both examples repeated the full native workflow and an additional current-input
check after freezing. The final record is
`graph-quality-20261104-source-scope-portable`.

| Example | Final candidate | Configured project tests | Result |
| --- | --- | --- | --- |
| Delivery | `ad604a06bc0e54cffb6b11f945177d6f7ab32161457b5a7ded3d27656c477425` | 9 | Passed |
| Team archive | `14bc442ec0948851214c1720927eefea7fc3c31b7679590224358e75348fd3cc` | 5 | Passed |

- [Delivery portable acceptance](examples-delivery-source-scope-portable-final-acceptance-summary.json)
- [Archive portable acceptance](examples-team-archive-source-scope-portable-final-acceptance-summary.json)
- [Delivery post-freeze current check](examples-delivery-source-scope-portable-post-freeze-check.json)
- [Archive post-freeze current check](examples-archive-source-scope-portable-post-freeze-check.json)

Exact staged-blob comparison covers 682 current inputs, including frozen model
files, managed runtime hashes, watched files and `.gitignore`; all match. Both
scope-input hashes are
`54080b35ebd8cdc86c951ccd6cc38f217e3c332ff71abf566ae9b994ad76713b`.
The unrelated historical `whitebox-v04/review.json` was excluded from staging;
its index blob still equals the existing Git HEAD authority.

[The diagnosis](clean-export-source-scope-diagnosis.json) and
[staged-input parity](example-source-scope-portable-staged-parity.json) preserve
the cause and verification. Earlier accepted phases and failed clean-export
attempts remain intact. The clean-export rerun is reported separately.

## v0.11.1 source-boundary acceptance

Both examples completed the full native workflow after the shared source-scope
policy was copied through managed upgrade. The final frozen record is
`graph-quality-20261104-source-scope`.

| Example | Final candidate | Configured project tests | Result |
| --- | --- | --- | --- |
| Delivery | `52f7100eaf2f1109431d974d9e35eedaa843bb4f130b7c89d7e698036e5c73d9` | 9 | Passed |
| Team archive | `7b8aa922f3b7c554bcdf6fc2241c87c65015bf5ba590dfaf342016b8c152c182` | 5 | Passed |

- [Delivery source-boundary acceptance](examples-delivery-source-scope-final-acceptance-summary.json)
- [Archive source-boundary acceptance](examples-team-archive-source-scope-final-acceptance-summary.json)

The exact generated-output declarations in `source_scope.prune` are:

| Example | Artifact paths |
| --- | --- |
| Delivery | `scratch`, reserved `review/runtime` |
| Team archive | `scratch`, `data/recordings`, `review/runtime` |

Both retain source discovery at `.`. Whole `review`, `data` and observer runtime
directories were not added as prune roots. Existing business-classification
exclusions remain separate from physical-source scope and continue through the
original entrypoint/implementation checks. Declared source bindings and watched
files retain their integrity checks. The scan reports list encountered pruned
prefixes with their categories and reasons; recording trees are skipped before
their contents are traversed.

Normal generation, sealing, scanning, explicit review, verification, acceptance
and current-input checks all passed. The original baseline hashes, protected
business/state source and independent expectations remain unchanged. Freeze
guards confirmed byte equality with canonical runtime, adapter and viewer files,
including the new `bo_observer/source_scope.py`. Earlier freezes remain intact.

The archive pre-review scan retained 21 existing implementation review items;
the explicit review records only unchanged classes/support source under the
existing acceptance rules. Final inspection and verification passed. No new
business requirement, test waiver or alternate baseline was introduced.

## v0.11.1 patch acceptance

Both examples repeated the complete native workflow on the original baselines
after the concurrent trace-lane and legacy data lifecycle caption corrections.
Runtime provenance and managed manifests identify release `0.11.1`. The final
frozen record is `graph-quality-20261104-clock-caption`.

| Example | Final candidate | Configured project tests | Result |
| --- | --- | --- | --- |
| Delivery | `4e7321beb3e13586bdc8c6202eab5bab8fafe16d4d47abb65e1d79a5d8fe6dda` | 9 | Passed |
| Team archive | `b493c735dcfec12d84f02e405abcb88773daefd2dbef56621237b09301459510` | 5 | Passed |

- [Delivery patch acceptance](examples-delivery-clock-caption-final-acceptance-summary.json)
- [Archive patch acceptance](examples-team-archive-clock-caption-final-acceptance-summary.json)

All generation, sealing, scanning, explicit review, verification, acceptance and
current-input checks passed. Freeze guards confirmed unchanged original
baseline hashes and exact equality with the canonical runtime, adapter and
viewer files. Protected business/state code and independent expectations remain
unchanged. The review notes explicitly identify event-order witnesses for equal
timestamps and the existing lifecycle resolver labels used by the caption fix.

Earlier v0.11 records remain intact. Delivery's earlier clock-only phase passed
and was frozen separately as `graph-quality-20261104-clock`. Archive's earlier
clock phase passed every native stage, then its freeze guard correctly refused
the canonical `graph-core.js` change made during that phase. The
[clock freeze-guard record](example-clock-freeze-guard.json) preserves this
refusal; the final candidate above was copied and fully reaccepted after the
caption fix froze. No native stage or freeze guard was skipped.

Only the managed example paths were staged by this integration task. Actual
browser tests, whole-repository checks, clean Git export and publication are
reported separately.

## v0.11.0 accepted candidate

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
