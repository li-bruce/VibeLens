# Native effect attempts and policy observation contracts

Status: focused/full regression, managed examples, fresh installation and clean
export passed. Fresh native trial acceptance remains pending. P7 is still in
progress. See [results](results.json) for commands and remaining scope.

## Original failure

`node-upgrade-original.zip` retains the complete upgrade diagnosis, sealed native
observations and the unchanged application/model/test inputs. Full verification
reported 353 mapping diagnostics. These were not 353 wrong business decisions:
all 233 policy steps had matching input/output values, but their custom adapter
used random call IDs and `control` dependencies instead of the existing policy
event contract. The list operation also used a rule whose business targets did
not include that operation. Browser cases were explicitly unrun, not discarded.

The effect check additionally assumed that a transaction identity appears in an
entry output, although this native adapter captured it as an input. It required
all four attempts in a successful case to commit; three were genuine rejected
requests with rolled-back transactions and failed owning business invocations.

## Shared repair

Effect completion checks now have their own module. They compare identities from
either selected entry direction and reject contradictory captures. Every related
invocation of the declared completion node still needs exactly one applicable
terminal belonging to that exact invocation.
An error can close an aborted attempt only with matching failed business owners,
the same native identity and no contradictory success value. It never satisfies
the successful completion expectation: at least one real successful completion
is still required. Unknown owners, missing terminals, duplicate terminals, wrong
identities and false completion values remain errors.

The policy gate retains all comparisons and reports call identity separately
from values. Skill references now spell out the existing native event IDs, data
dependencies, real business parent and shared operation-use bindings. This guides
custom adapters without changing application decisions or rerunning predicates.

## Evidence so far

- `effect-first.log`: three failures demonstrate entry-input rejection, mixed
  commit/rollback rejection and an undetected conflicting start identity.
- `effect-retest.log`: the first 52 concept/effect tests passed.
- `focused.log`: all 79 effect, concept and policy tests passed, including
  wrong-owner/producer, duplicate-terminal and missing-completion counterexamples.
- `native-replay.json`: replay of the exact sealed Node events removes both
  false transaction diagnostics. All 331 real policy-wiring diagnostics and the
  undeclared list-operation association still fail. No native execution or record
  was changed to produce this diagnostic result.

The first replay command combined stderr into its output; it is preserved as
`native-replay-combined.log`. The separate stdout JSON rerun uses the same inputs.
The Node chat repaired its own adapter and list-use bindings through the normal
workflow, preserving business behavior, assertions and capture requirements.
`node-policy-repair.zip` retains the controlled before/after executions, source
snapshots, confirmation and checksums. Both versions passed 15 direct-native
checks in each of on/off/fault mode. All 44 permission decisions per mode and
business outcomes agree. The enabled run's 275 step-identity errors, 121 data
dependency errors and nine list-use ownership errors are now absent. The focused
case still reports the ten missing full-workflow policy cases; it does not replace
the complete native verification or browser recording.

The public [Python dialogue](python-dialogue/dialogue.md) and
[Node dialogue](node-dialogue/dialogue.md) are checkpoints through these repairs.
They identify simulated user messages and technical coordination, and are not
independent human usability evidence. Later iterations remain outstanding.

`full-verify-retest.log` reports 1,171 tests in 105 Python unittest suites, with
one existing skip, plus the maintained JavaScript and pinned TLC checks. Both
managed examples passed verify/accept/check and observer-free package execution.
`source.json` covers 245 Python and 142 JavaScript maintained modules.
The fresh installation retains all 460 maintained files byte-for-byte. The clean
Git export passed both examples using frozen approvals without regeneration or
reapproval; this result is separate from the still-pending independent trials.

The first staged whitespace check reported an original Markdown hard line break
inside the exported Python dialogue. Its bytes are retained; the narrow evidence
attribute preserves that transcript while maintained source checks stay strict.
