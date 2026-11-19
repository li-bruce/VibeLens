# P1 domain and shared-rule definition checks

Candidate branch: `feat/behavior-contracts-sequential`. This builds on the scalar
definition slice and preserves the approved P0 baseline. It is not full P1 or a
new dialogue/runtime acceptance run.

The [machine-readable result](results.json) records each command, exit code, log
path and the exact log checksum. All six commands passed:

- 25 domain, collection-expression, identity and shared-policy tests.
- 38 existing scalar/CLI contract tests, unchanged.
- 6 plan-order checks and 3 frozen-forest checks, unchanged.
- Source syntax, lint and formatting: 200 Python and 136 JavaScript sources.
- Managed runtime package consistency.

The expectations include hand-calculated finite counts, reordered sets/maps,
duplicate keys, typed JSON identities, unbounded queue contents and growing object
identities despite a live-instance cap. Native predicates remain opaque and are
never evaluated by interpreting their names. Public JSON validation rejects a
negative collection bound and duplicate set values.

The validator reports definition capabilities separately from native binding and
formal analysis. Neither native observation nor a model checker ran in this slice.
The [implementation status](../../../development/behavior-contracts/p1-definition-slice.md)
lists the remaining P1 work. P2–P7 and A01–A34 remain pending in the work ledger.
