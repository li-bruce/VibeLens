# P1 scalar definition slice

Status: this slice is checked; P1 remains incomplete.

The [implementation note](../../../development/behavior-contracts/p1-definition-slice.md)
lists delivered behavior and the remaining P1 work. No existing project or Skill
workflow automatically adopts this contract yet. Native execution is unchanged.

The new definition/CLI suite passes 38 tests. The unchanged model, concept,
dialogue, confirmation, protocol and document suites pass 116 tests; the frozen
forest fixture passes 3. Packaging and source checks pass. The source check covers
197 Python and 136 JavaScript files. Managed runtime copies were regenerated with
`tools/sync_runtime.py`; application declarations and personal files are preserved.

The checks include malformed versions/fields, model-qualified ownership, missing
reads, incomplete write/unchanged partitions, canonical transition updates,
contradictory initialization, unknown parameters, type errors, unsupported number
identity, and read-only CLI behavior. All cases have independent expected outcomes.

[results.json](results.json) pins source hashes, command scopes, exits and logs.
The P0 full-run evidence remains separate. No A01–A34 case or later phase is marked
complete on the basis of this partial P1 implementation.
