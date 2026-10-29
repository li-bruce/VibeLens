# Independent frozen-version file-sharing trial

Conversation: `01a18512-6617-7791-aa29-f2aeb9312859`. The coordinating AI supplied scripted user answers. This is an independent implementation and automated acceptance exercise, not independent human approval.

| Round | Result | Original evidence |
|---|---|---|
| Initial frozen application | 24 tests, 60 scenario runs and 78 business assertions passed | [Acceptance](native-evidence/initial-acceptance.md), [design dialogue](native-evidence/design-dialogue.md) |
| Selected-recipient revocation | 35 tests, 84 scenario runs, 282 assertions and 10 negative evidence checks passed | [Acceptance](native-evidence/revocation-acceptance.md), [summary](native-evidence/revocation-summary.json) |
| Native `b78f03a` framework upgrade | Formal checks passed; overall acceptance failed the original keyboard-source path | [Round index](native-evidence/framework-upgrade-b78f03a/index.md), [summary](native-evidence/framework-upgrade-b78f03a/summary.json), [failed test](native-evidence/framework-upgrade-b78f03a/keyboard-source-acceptance.json) |
| Focus repair `3458366` | Original business/evidence checks and unchanged keyboard path passed | [Final round](native-evidence/framework-upgrade-3458366/index.md), [summary](native-evidence/framework-upgrade-3458366/summary.json), [canonical regression and repair](../../../semantic-focus/README.md) |

The revocation recording contains 1,731 events and 11 snapshots, with zero errors, drops and gaps. Its bounded queue drained in 363.125 seconds. The [drain analysis](native-evidence/revocation-drain-analysis.md) and [read-only binding profile](native-evidence/binding-readonly-profile.log) retain the measurements. Real-time performance has not passed; a smaller later recording does not establish a performance improvement.

The failed b78 upgrade retained all original business expectations and used no compatibility shim. Its correct HTTP source response and successful alternative menu did not override the failed keyboard interaction. The final repair passed that byte-identical keyboard test without an explicit rerender workaround. Full-file source/highlighting/version checks, real Boolean dependencies, short-circuit negatives, authorization filtering and native 2D/3D passed on a new 429-event recording. The new queue drain took 121.584 seconds under overlapping verification load; it does not establish a throughput improvement.

The [visible conversation](dialogue.md), [failed-round evidence manifest](native-evidence-manifest.json), [final-round evidence manifest](final-native-evidence-manifest.json), original source/evidence archives and failed browser screenshots remain available. Each framework-maintenance round is recorded separately from initial development and business iteration. Core acceptance completed before promotional/demo page work resumed.
