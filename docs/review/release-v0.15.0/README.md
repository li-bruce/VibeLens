# VibeLens v0.15.0 release verification

This release combines the [multi-model acceptance](../model-networks-20261112/README.md)
with [dependency-delivery acceptance](../dependency-downloads-20261112/README.md).
The latter records real primary/GitHub downloads, cold installation, offline
reuse, package parity, managed example upgrades and release checks.

Original application definitions and required regression assertions are retained.
Evidence distinguishes delivery failures, implementation fixes and successful
retests; checksums do not claim a reproducible native Wasm rebuild.

Release checks passed: the complete `tools/verify.py --database` gate, 188 Python
and 130 JavaScript source checks, both frozen examples from a clean Git export,
real CDN/GitHub downloads and six cold-package browser checks in 2D/3D with
recording and iteration. The default ZIP is approximately 0.92 MB, with a
separate offline ZIP. `package-manifest.json` records the final package inventory.
