# Repair 27 — preserve recording ancestry and finish reviewer preparation

The consolidated issue list is [next-round.md](../next-round.md). This batch
addresses its shared recording defect and reviewer preparation failures. P7
remains in progress; a passing repository gate does not accept either native
trial or replace an earlier failed recording.

## Failure and repair

The second Node recording began after 2099 events. Its context retained only the
last 2000, starting at sequence 100, although the history still contained all
2099. An actual parent entry at sequence 67 was omitted. This produced 446
missing-parent references in the retained context; the 8178 interval events had
no missing parent references. The original record remains unchanged and failed.

The shared context selector now keeps the existing recent-value limit and closes
selected facts over available invocation boundaries. Older parents and their
actual returns are metadata-only. Private boundary candidates also let a later
asynchronous child identify a caller completed before recording began. Original
event IDs, phases and times are preserved. No invocation, return or end time is
inferred from labels or proximity. Missing or expired required evidence still
produces a gap; queue and history capacities are unchanged.

Full and focused recordings use the same ancestry logic. Focused capture still
avoids evaluating unselected value builders. An explicit missing parent ID never
falls back to another invocation with a reused call ID. The additive
`context_selection` field reports deliberately omitted older values separately
from actual ownership or capture gaps.

## Focused evidence

- `context-before.log`: one actual checkpoint regression failed before the repair;
  nine additional new API tests could not yet run. These are not ten independent
  reproduced defects.
- `context-after.log`: all ten context-window cases pass, including reused IDs,
  producer scope, closed ancestors, unavailable history and cyclic references.
- `native-context-after.log`: eleven capture-context integration tests pass,
  including consecutive full/focused recordings with actual probe events.
- `targeted.log`: all 94 targeted recording, settlement, retention and receipt
  regressions pass. Existing negative assertions remain intact.
- `original-record-diagnostic.json`: read-only reconstruction from the frozen
  source facts retains 2000 recent values and two older boundary headers. The 8178
  interval facts remain identical and the computed missing references become
  zero. This is a diagnostic calculation, not a new native run or acceptance.
- `source-before.json` and `source.log`: the first source check rejected the
  formatter's default line length. Formatting with the repository's declared
  settings passes in `source-formatted.log`; behavior is unchanged.

## Reviewer changes

Search results expose their existing stable graph identity through
`data-result-id`. The maintained `tools/test_trial_captions_browser.py` selects
that exact result, retaining the full-file and declaration-highlight assertions.
It no longer assumes `prepare_download` cannot also match
`guard_prepare_download`.

`tools/test_trial_controls_browser.py` separates an optional interaction diagnosis
from its default native acceptance mode. The default still requires real producer
history, unchanged native database rows and no observer self-events. Diagnosis
reports native exclusion as untested. The original discovery failures remain in
[discovery-round-27](../discovery-round-27/README.md).

Both managed examples were regenerated, inspected, verified, accepted and checked
after confirming their configured business sources match the preceding commit.
Full repository verification, fresh installation and final native/UI checks are
recorded separately as they finish. Product scenes follow accepted trial evidence.

## Environment failures retained

The first full gate stops at five Node migration assertions because sandbox
`realpath` returns `EPERM` for temporary fixture directories, before reading the
test JSON. The unchanged migration suite passes all 16 tests on the host
(`migration-host.log`). The complete gate is consequently run on that same host;
no migration assertion or source containment rule is changed.

Fresh Skill installation passes offline. Its separate JavaScript parser setup
cannot use the sandbox's empty npm cache (`ENOTCACHED` for locked TypeScript
5.9.3). The documented lockfile-based `npm ci` succeeds on the host. This installs
generated dependencies only; maintained package bytes are checked separately.

## Repository and package result

The complete `tools/verify.py --database` host run passes. Both examples
have new frozen acceptance records, and clean-export validation passes.
All 466 maintained files in the fresh installation match this candidate,
including after locked parser dependency installation. See [results.json](results.json).

The Python maintenance run, Node semantic iteration/source refactor and
their desktop checks remain separate pending P7 gates. No original failed
record was edited and no new dialogue was opened for this repair.
