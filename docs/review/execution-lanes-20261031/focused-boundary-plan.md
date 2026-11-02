# Focused capture keeps real invocation boundaries

Trial 07 confirmed full capture ownership and strict closure, then reproduced a
separate gap through actual Web controls. Selecting only
`policy:actor_is_recipient` recorded its true output but filtered the enclosing
request/action entries. The original recording has a dangling parent call and
the viewer correctly reports unassigned observations. This is partial focused
capture evidence, not a complete execution trace. The coordinator initially
required minimum boundaries, then the human directly allowed truthful disclosure
of missing ownership in local recordings. Keep both answers and their order.
The following repair improves focused inspection; it does not introduce a new
user acceptance gate. Complete-capture strictness remains unchanged.

## Implementation contract

- Keep selected node/descendant value builders. Unselected builders never run.
- Retain actual filtered span entry/exit metadata with original identity, phase,
  time and parent chain; no argument/result copies. Native data calls already
  entered before selection must retain their actual exit metadata too.
- Mark metadata explicitly as `context_only` with a physical `context_boundary`.
  Strict schema forbids value bodies and malformed boundaries. A full acceptance
  run cannot pass by substituting partial metadata for value observations.
- Keep a bounded collector cache of witnessed open invocation entries, independent
  of ordinary history expiry. Event-batch preflight must copy this state. Report
  actual cache/budget loss as a gap.
- A focused recording retains selected facts and only the real ancestor boundaries
  needed to explain them, including calls already open at recording start.
  Preserve source IDs and caller identity; never reconstruct parents from time.
- Graph and Timeline use those boundaries for intervals and grouping. Metadata
  stays out of ordinary replay steps and has no invented value or outcome.
- Regressions cover Python/Node lazy builders, concurrency, nested/native calls,
  mid-call selection, history expiry, stop/restore and bounded loss. Then repeat
  actual single-rule browser capture, full repository checks and a new dialogue.

Do not alter the frozen trial 07 evidence or its protected baseline. The current
point-ownership checkpoint and its complete repository run remain valid evidence
for full capture; this new repair is a separate managed update.
