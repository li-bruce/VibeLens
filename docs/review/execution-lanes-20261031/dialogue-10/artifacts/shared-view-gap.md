# Shared control plan and typed projection mismatch

The standard HTTP dispatch fix works in this trial. Activation, inventory, planning and publishing use the model-only context successfully while the real live view exceeds the unchanged 8 MiB CLI budget. The next blocker is the adjacent permission view, not HTTP transport.

The actual conversation request is preserved in `request.txt`. `chain-permissions-view.json` keeps the upload/review/share/read anchors, business/decision node types, flow/guard/data relations, both directions, depth 2 and native layered layout. The canonical planner returns a valid plan containing `state_new`. The installed CLI publishes revision 2, then the real scoped Chrome page acknowledges **rejected**:

```text
Requested nodes are hidden in the resulting view: state_new
```

`permissions-browser.json` independently retains the loaded graph. `state_new` and original `transition:submit` are absent; the other 22 planned nodes are visible. No page exception occurred. The viewer correctly rejects the incomplete result. The failure survives native reload. `permissions-scoped.png` and `permissions-reload.png` show that actual page; no applied claim is made for this view.

`shared-view-gap.json` retains the exact current context identity, canonical valid plan, missing node declaration, related edges, real rejection and byte parity for the relevant installed/canonical Python and viewer modules. `control_gap.py` recreates that plan from the live model without changing the business application or viewer. Source inspection indicates an inconsistency between planner-selected out-of-type nodes and the native view's one-hop filter boundaries. This is a diagnosis from the retained model and source, not a repaired implementation.

The initial depth-0 view did apply and remains separate evidence (`browser-control.json`). It does not substitute for the requested permission-inclusive view. Filtering and replay of the exact stopped current-build recording remain **not run** after this defect; no alternate view or offline snapshot was used to bypass the failure. No accept, shared-source patch or managed-file hand edit is allowed in this trial.

After canonical repair, use the normal upgrade interface with the same baseline and active change. Recompute the interpretation for the new build, retest this exact permission view and native applied acknowledgement, then filter the explicit stopped recording of that build and inspect actual replay and raw preservation. Keep the failed fast-load collection health separately: its queue dropped events, whereas the 153-event stopped interval has complete parent/exit coverage. Do not reset those old counters or call the entire history gap-free.
