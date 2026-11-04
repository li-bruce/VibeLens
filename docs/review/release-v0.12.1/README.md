# VibeLens v0.12.1 patch review

Local release checks passed on 2026-11-05. Publication is handled separately.
The independent conversation trial remains **in_progress**; it is not included
in a completed end-to-end claim.

This patch follows the immutable [v0.12.0 release](../release-v0.12.0/README.md).
Its tag, ZIP, original approvals and expected application contracts are retained.

## Findings and repairs

| Finding | Repair and evidence |
| --- | --- |
| Source-free draft crashes on missing `presentation.subject` | Use the existing project identity; no fake runtime object. [Original error and browser retests](../release-v0.12.0/dialogue-findings/draft-viewer/README.md). |
| Arrange leaves stale cached bounds for Fit | Recompute current visible glyph and region bounds; browser checks every visible object against the viewport. [Geometry regression](../release-v0.12.0/dialogue-findings/draft-viewer/fit-regression.md). |
| Design reaches unsupported multiple-state-model binding | Check capability before confirmation and preserve the original rejected draft. The single-model limitation remains. [Trial finding](../release-v0.12.0/dialogue-findings/multiple-state-models/README.md). |
| Public browser CI lacks instrumentation dependency | Install existing `requirements-telemetry-test.txt` in that job. [Original public failure](../release-v0.12.0/checks/github-tag-browser-failure-summary.json). |
| A declared transition effect and its matching explicit crosslink draw twice | Consolidate only proven-equivalent associations, retaining all original IDs, assertions and binding obligations. [Actual trial reproduction and regressions](../release-v0.12.0/dialogue-findings/effect-relations/README.md). |

## Validation

Checks run against a frozen canonical source. Shipped examples migrate from new
v0.12.1 baselines through their existing review, verify, accept and check commands.
Native application source, machine meaning, intent, acceptance, whitebox and
mapping contracts must equal the preserved baseline.

| Check | Result and evidence |
| --- | --- |
| Full original suite, including database checks and new effect regression | [Passed](checks/full-verification-final.json), 485.63 seconds |
| Maintained source syntax, lint and formatting | [Passed](checks/source-quality-final.json), 164 Python and 107 JavaScript modules |
| Source-free design browser: shipped fixture | [Passed](checks/design-browser/shipped/result.json), five check groups, no browser errors |
| Source-free design browser: actual original failure | [Passed](checks/design-browser/original/result.json), five check groups, no browser errors |
| Source-free design browser: actual repeated-effect draft | [Passed](checks/design-browser/effects/result.json), five check groups, no browser errors |
| Accepted conceptual application and browser | [Passed](checks/concept-browser.json), all five verification categories and seven browser groups |
| Managed copies and both shipped examples | Migrated and accepted from preserved baselines; [receipts frozen](checks/freeze-examples.json) |
| Complete Skill ZIP and fresh extraction | [Passed](manifest.json), all 351 file hashes match |
| Clean Git export with frozen approvals only | [Passed](checks/clean-export.json), 53.01 seconds; no regeneration or reapproval inside the export |
| Final real-index export after staging | [Passed](checks/real-index-export.json); both examples are current, with frozen approvals only |

The design browser measures every visible glyph and expanded region against the
viewport after Expand, Arrange and Fit. It also checks empty runtime facts and
unchanged input bytes. [The effect draft screenshot](checks/design-browser/effects/states.png)
shows the resulting state view. The retained application browser records an actual
upload (HTTP 201), share (HTTP 200), scoped nine-event capture and a completed
9.07 ms business interval in [Graph and Timeline](checks/concept-browser/focused-business-timeline.png).
The selected lifecycle and values are readable; graph captions in that overview
are small and truncated at 18% zoom. Cross-layer lines can still cross. These
results establish functional behavior, not a claim of polished layout in every view.

Frozen accepted candidates:

- Delivery: `264ed58a945bbe2a966bb83d92ff2479e97b1d5d8dc481212b0744694d59b241`.
- Team archive: `57ebbe17c82673cd3f11fcc5b90ff1f805bbcca094a575a017cf60159dd88dd3`.

Each example keeps its new receipt under `.release/stategraph/release-v0.12.1`.
The prior v0.12.0 receipt directories remain byte-identical. The package was built
from a private Git index; the working repository's real index was not changed.
The public release/Pages/CI jobs still need their separate post-push verification.

Before publication, comparing the private export with the real index found one
older receipt with different line endings: `whitebox-v04/review.json`. The private
index captured the working copy's 27 CRLF endings; the real index retains the
original HEAD blob with LF endings. Its JSON is identical, and the Skill, native
source and new receipts are identical between those trees. The historical blob
is preserved. [The comparison](checks/export-tree-comparison.json) records both
hashes; the original private-export result is retained separately from the
passing real-index export check. Final delivery tree:
`71550819c5f501dbc899666f6fbd876801724c89`; team archive remains
`6a389a433aa24031db1d84e0977ec3cb8dc84476`.

## Retained attempts

The first full-suite attempt stopped at the Windows directory-junction tests:
the sandbox refused their `mklink /J` commands. The unchanged source-file tests
then passed all eight cases with native Windows permissions. The
[failed attempt](checks/full-verification.json), [targeted retry](checks/source-files-native.json)
and final complete run are retained. No test or timeout was weakened.

An initial example migration and source check preceded the additional effect
projection correction. Their `initial` logs and source-quality report remain;
`effect-final`, `source-quality-final` and `full-verification-final` describe the
final source. Inspection before review correctly refused the missing or stale
review; the protected contracts were then compared and the ordinary workflow
completed. The original draft/fit/effect failures remain with their findings.

## Independent conversation

The [separate conversation](../release-v0.12.0/trial-session.json) installs the
published package and receives simulated user answers authorized by the user.
Its original multiple-model draft was rejected. The positive trial explicitly
uses file review as its bound primary model and retains separate login and grant
objects, rules and observations. It remains in progress.

## Publication and subsequent browser-check repair

The [public release](checks/remote-release.json) and installation archive are
available. The [downloaded ZIP](checks/remote-download-and-pages.json) matches
the frozen SHA-256 above. [Pages](checks/remote-pages-published.json) serves the
v0.12.1 link and the same viewer source bytes.

All eight jobs for main commit `3f10d928` passed, including the real database and
browser jobs; see [the retained CI result](checks/remote-main-ci.json). The first
tag run passed seven jobs and failed one browser assertion during an asynchronous
reroute. The same product source passed that browser job on main. The
[diagnosis and retest](checks/execution-routing-diagnosis.md) preserve the failed
artifact and both normal and mid-span checks. Commit `b88b5562` fixes the test's
frame sampling while retaining its endpoint-count and accuracy assertions.
Published Skill, managed runtime and ZIP bytes remain unchanged.

The independent user-visible conversation is separate from these repository
checks. Its [implementation checkpoint](../release-v0.12.0/dialogue-findings/implementation-followup-20261105.md)
contains actual responses and observations, but its final browser acceptance and
business iteration are still pending. Do not read the passing repository checks
as a completed fresh-conversation trial.
