# Visible-content enclosure repair

The saved six-table database layout reproduced the reported circle expansion.
The old spatial calculation included the hidden database owner's saved position,
then used half the bounding-box diagonal plus a fixed margin. The owner was at
Z = -4104 while its visible tables were at Z = 304–1446.

The repair fits the visible glyph disks and nested child-region disks with
[D3 `packEnclose`](https://d3js.org/d3-hierarchy/pack#packEnclose), already pinned
in this repository under ISC. Both renderers share the fitting helper and a
12-unit region margin. Planar fitting includes each visible glyph and its actual
label rectangle, using corner points instead of the old glyph-centered diagonal.
Spatial fitting includes its visible solid bodies. Invisible owner anchors do
not contribute.

The real saved-coordinate case changes from radius **2882.18** to **747.11**.
IDs, pinned flags, positions, declarations and execution evidence remain intact.
Real self glyphs remain part of bounds. Child-region radii are enclosed in full.
An owner whose visible contents exist only on other layers keeps those occupied
projections; its external edges connect to a real projected rim. Empty circles
are not created at the hidden owner's old location. If all children are hidden,
the shared view presents the owner as a normal glyph; restoring the children
restores its region without changing the saved expansion preference.

Run `node docs/review/graph-quality-20261104/enclosure/run.mjs` from the repository.
It loads the original spatial calculation at revision
`7f7907d247beb76f1eae7995664155022d12a890`, records the expected failed assertion
in [before.json](before.json), and records eight passing geometry checks in
[after.json](after.json). The new regression includes the actual saved positions,
visible self glyphs, nested cross-layer regions, filtering, folding, moved leaves,
exact rim ports, planar fitting, nearest-visible containment ancestors, retained
business-only owner glyphs, metadata preservation and 10,000 visible disks.

A compatibility regression was caught during the repair: requiring an owner ID
inside the old region member list broke an existing internal self-node edge test.
The fix preserves that existing behavior for occupied owner-plane regions and
uses projected rims only when the owner has no occupied plane of its own.
No assertion was weakened.

The complete release gate then caught an existing label-containment requirement
in `examples/delivery/tests/test_graph_layout.mjs:200`. The initial planar repair
had fitted glyphs alone. It was corrected to enclose the actual label rectangles
as well. The unchanged existing layout suite now passes; its retest is recorded
in [the retained log](../examples-delivery-layout-label-retest.log). The initial
targeted result remains in [after-initial.json](after-initial.json); the current
strengthened tests include rectangle corners explicitly.

These are geometry and routing checks. The full release gate and real browser
acceptance are recorded by the parent review; this folder does not substitute for
those checks. Camera-dependent icon enlargement is a rendering affordance and
does not move saved nodes or continuously change semantic enclosure geometry.
