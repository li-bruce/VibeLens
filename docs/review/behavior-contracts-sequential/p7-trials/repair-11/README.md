# Check intermediate snapshot admission

Status: focused, source, managed-example and complete regression checks passed.
Native retest and the remaining P7 obligations are pending.
P7 remains open.

## Reproduced failure

The Python drive trial's prior strict verification passed all five reports and
132 assertions. Its local sink only appended events and snapshots. Independent
SQL reads verified the final projection but did not exercise intermediate
snapshot admission. The queued-job sequence submitted revision 1 with
`context.allowed=true`, then read the same revision with `allowed=false` after
revocation. The collector correctly rejects the latter as conflicting content.

`prior-python-evidence.zip` retains the original trial verification, raw strict
observations, diagnosis, exact conflicting envelopes and scope/process receipts.
The manifest records every file hash. `prior-python-strict-admission.json` replays
those original facts through the shared reducer: 106 snapshots checked, exactly
one rejected at queued_revoked position 8. The original strict pass remains
valid only for its original scope. No original HTTP response body exists for
this locally reproduced conflict.

## Changes

- `observation/snapshot_admission.py` is the common live/offline identity,
  evidence, owner and complete-version reducer. Live frame retention is unchanged.
- `workflow/snapshot_evidence.py` replays each enabled run in isolation, retaining
  submitted order. A final projection cannot replace omitted intermediate facts.
- `verify` automatically checks canonical snapshot sequences. Existing closure
  requirements also require snapshots for canonical events with explicit state
  revisions. Legacy events retain their original checks and are labelled outside
  this canonical check's scope. Off/fault native-effect checks are unchanged.
- Rejected admission and missing evidence fail mapping; accepted but invalid
  native states are reported under state rules. No application transition runs
  in the observer.
- Initial setup, native bindings and iteration recall distinguish complete
  versioned context from typed per-operation inputs and evaluated rule facts.
  No source version is advanced solely for the observer.

## Evidence so far

The new regressions reproduce the list-only sink blind spot, missing frames,
reordered facts, identity/build/revision mismatches and separate state errors.
Python and Node native executors both evaluate a changing typed input without
changing context. Shared live-read, multi-model, batching and iteration checks
remain in the focused suite.

The first wider focused command omitted the workspace TEMP override and hit the
known Windows sandbox temporary-directory permission boundary. Its log/exit is
preserved in `focused-temp-failed.*`. The same tests with the normal workspace
TEMP/TMP settings passed: 69 tests. No application assertion was changed.

## Strict duplicate identity follow-up

After the first complete regression passed (1,148 reported tests), a separate
negative control found Python equality treated `context.slots=1`, `true`, and
`1.0` as the same retry when revision and evidence ID were unchanged.
`duplicate-json-type-before.json` and `duplicate-json-type-first.log` preserve
the accepted wrong-type retry and three failed assertions. The native observer
now compares canonical JSON digests before accepting a duplicate. This matches
the shared read-frame contract and does not change native execution.

The first full run, managed approvals, source result and installation identity
are retained under `before-json-type-*`. They do not certify the final patch.
The strengthened focused rerun passed 71 tests; final managed, full-run and clean
export receipts must refer to the final source. The first candidate installation
remains intact; the final trial uses a fresh `admission-final-skills/vibelens` candidate after the HTTP follow-up below.

The managed-copy review initially stopped because this follow-up also changed
`bo_stategraph/__init__.py`, which the earlier repair helper had not allowed.
The helper now verifies that exact file against canonical `bo_stategraph.py`
before admitting it as a regenerated dependency. Existing source equality,
change allowlists and all verification/accept/check gates remain enforced. The
original failure is retained in `typed-copy-first-*`.

The final isolated Node dependency installation first encountered Windows
sandbox EPERM while creating package directories. A normal host `npm ci` with
lifecycle scripts disabled succeeded against the unchanged lockfile. Installed
maintained files are independently hashed in `installation.json`.

## Rejected HTTP connection follow-up

The second full run stopped at the unchanged wrong-token assertion in
`test_remote_event_batch.py`: Windows reported ConnectionAbortedError/10053
instead of delivering HTTP 403. `before-http-close-full-verify-retest.log`
retains the failure. The handler returned before consuming the rejected request
body, then fully closed the connection. This matches the reset risk described
in [RFC 9112 section 9.6](https://www.rfc-editor.org/rfc/rfc9112.html#section-9.6);
no packet trace was captured, so it is not a proven diagnosis of that OS reset.

`web/http_close.py` sends the unchanged rejection first, half-closes output,
then drains at most 64 KiB for at most 250 ms. Tokens, origins, payload limits
and all business/event admission checks remain unchanged. The body is discarded,
never parsed or admitted. Already-read invalid JSON keeps the normal error path.
Tests include 40 consecutive real rejected-body responses, a client that has not
yet sent its declared body, bounded cleanup and disconnection.

The complete runner passed 1154 reported tests across 103 unittest reports, alongside the JavaScript and pinned TLC checks. See `results.json`. Clean Git export is checked separately before commit.

Clean Git export passed for both frozen example approvals (`clean-export.json`). The full runner reported one existing filesystem-link test skipped because this Windows host cannot create symbolic links. Native trial acceptance remains pending.
