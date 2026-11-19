# Maintain behavior evidence through an iteration

Use the existing project iteration commands. `recall` restores the current model
inventory, assumptions, missing bindings and affected declarations. `begin` also
records recall; `inspect` refreshes it after edits or a restart. Read the compact
summary and the relevant source references before coding. Full changes stay in
`behavior-impact.json` and the canonical project artifacts.

## Decide which work is required

| Change | Work |
|---|---|
| Business meaning, state target, guard, completion or property changes | Review the changed region against the actual request and retain its confirmation |
| Function move, split, callback or probe change | Rebind and run source/runtime checks; resolve source facts in coding |
| Shared rule or interaction changes | Include every declared consumer, including hidden models |
| Analysis bounds, environment or checker configuration changes | Refresh affected analysis evidence and retain the precise assumptions |
| Labels, locale or personal layout changes | Keep stable identities and unchanged semantic evidence; check presentation |

For a changed behavior declaration, add a `behavior_changes` entry to the existing
`review.json`, keyed by the exact record shown in the meaning diff. Its value is
the list of recorded requirement IDs authorizing that change. Each ID must belong
to the change's original `requested_requirements`, still exist in intent, and have
an explicit `requirement_changes` explanation. For example:

```json
{
  "behavior_changes": {"actions/start-download": ["R7"]},
  "requirement_changes": {"R7": "Queued downloads recheck access when starting, as requested"}
}
```

This accompanies existing scoped discovery confirmation; it does not replace it.
Do not add an invented requirement to approve a code defect. Correct a defective
implementation against the already confirmed declaration. Removing a property or
changing a mandatory analysis profile requires the same explicit record-level
basis. Changing an analysis-only bound does not impose a new application limit.

## Read results separately

Verification retains original gates and adds coverage for intent, definitions,
mapping, capture, native state rules, business outcomes, project checks and each
optional analysis profile. Each category has its complete configured denominator,
actual evidence and missing identities. A required gap blocks acceptance.

Native observations can accurately record an invalid application value: mapping
can pass while the state/domain result fails. An analysis-only limit is reported
as an analysis finding and never changes the application. Missing, stale,
incomplete and unsupported analysis are distinct from a completed passing result.

Saved receipts retain their exact semantic prerequisites, source/build inputs and
tool fingerprints. `inspect` explains why each previous native receipt remains
current or becomes stale. The original exact-candidate acceptance check still
runs; a reusable scoped receipt cannot accept a new batch by itself.

The integration uses explicit workflow commands in the activated conversation.
It reports `automatic_host_hook: false`; no unsupported global editor hook or
cross-conversation activation is assumed. An unreviewed source revision remains
pending until the existing inspection, verification and acceptance gates pass.
