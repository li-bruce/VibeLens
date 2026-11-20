# Repair 24 — 3D caption overlap and context menus

Python's source-refactor trial passed its native checks and five desktop suites.
A separate bilingual inspection then found that right-clicking the cancellation
permission icon selected a different node. Two independent actual-page checks
reproduced the mismatch; collapsing and fitting the view did not remove it.

The rendered icon had the correct identity and caption. Another node's DOM
caption covered its screen position. Left-click dragging already picked the icon
behind that caption, but the right-click event bubbled to the planar handler,
which selected the covering caption's `data-node-id`.

Node and region captions now use the same 3D hit resolution for both actions.
A visible icon takes precedence; clicking unoccupied caption space still opens
that caption's owner. The handler stops propagation before the planar fallback.
Graph identities, source bindings, native execution and captured facts are unchanged.

`test_spatial_interaction_bounds.mjs` covers node/ring labels, actual glyph
precedence and label ownership over empty or edge space. The real trial view
runner now detects a separated icon covered by another caption and checks the
selected identity. That new check also failed against the original installation
for a second rule node, independently of the cancellation label.

Original results and screenshots are retained in `before.zip`. Shared regression
and final source checks passed; the [receipt](regression.json) counts 1304 reported
tests across 116 unittest reports, including repeated suites and one existing
skip. Fresh-install actual-page retests remain required. P7 remains open.

The first full regression stopped at the example's managed-file guard after
canonical copies were synchronized but before their ownership seal was reviewed.
`full.log` retains that rejection. This is a root-run preparation-order error:
configured application sources are compared byte-for-byte with Git, managed
assets with the canonical source, and the original example verification follows
the reviewed seal. No checksum guard or assertion is removed for the retest.

The first clean export also rejected both examples: their current working
approvals were valid, but their frozen release pointers still selected the prior
candidate. `clean-export.log` preserves this separate preparation-order error.
The new accepted records are frozen under a new name before the second export;
the exporter itself remains read-only with respect to approvals. Both source
guides now state the complete synchronization, review, freeze and export order.
The [second clean export](clean-export-retest.json) passed both examples against
their frozen current candidates without regeneration or reapproval.
