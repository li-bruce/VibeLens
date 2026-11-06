# Readable conceptual routes

The default `cluster` layout now uses ELK directional layout inside business,
state and rule planes and their expanded conceptual regions. Structural views
retain type/source clustering. Both renderers use the same planar coordinates.

| Plane | Ordering evidence |
|---|---|
| Business | Declared flow, event handoff, join, retry and cancellation relations |
| State | Declared transitions and their target states |
| Rules | Input/predicate dependencies leading to decision results |

Rule dependency order is not an observed evaluation sequence. Loops remain loops;
shared predicates/actions keep one identity. Cross-plane mappings and business
guards do not impose business sequence. No layout operation creates graph facts.

During initial design and each affected iteration:

1. Reuse confirmed network membership, state objects and policy dependencies.
2. Distinguish automatic handoff from a later independent user action. Clarify only
   unresolved meaning; do not add workflow stages for a neater drawing.
3. For several named routes, optionally add `discovery.presentation.routes` using
   existing canonical concept and edge IDs and actual `source_refs`:

```json
{"routes":[{"id":"recipient-read","nodes":["share","read"],"edges":["share-read"],"source_refs":["U1"]}]}
```

4. Run the ordinary concept validation. A route must be connected within one
   conceptual plane and contain declared ordering edges. A node may belong to
   multiple routes; it is displayed once. Invalid/stale references fail.
5. Refresh the graph and affected source/runtime checks. Route labels influence
   layout tie-breaking only; confirmed meaning, IDs, bindings and recording
   witnesses remain unchanged. Source refactors require new bindings, not a new
   business sequence. User positions and pins survive ordinary refreshes.

Use the existing Arrange action to reflow an established view. Newly opened
conceptual regions receive directional placement while saved descendants remain
in place. Exact pins take priority; contradictory pins can retain backward links.
Dense cycles cannot have every edge forward. Large layouts run through the bundled
ELK worker; geometry is not recomputed on each replay step.
