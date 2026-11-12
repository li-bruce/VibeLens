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

## Published artifacts

GitHub published v0.15.0 from merge commit `59a72cd5`. The release and Pages
workflows both succeeded. `published-manifest.json` records the actual release
hashes; `published-verification.json` records a downloaded ZIP's size and SHA-256.
Every file in that ZIP was verified, and all four published archives reproduce
locally from the committed bytes.

The earlier local `package-manifest.json` used CRLF in four documentation files;
Git exports those files with LF. Matching the already-committed LF text produces
the published hashes. Executable source and downloaded dependency bytes are
identical in both checks. The earlier local manifest remains as evidence rather
than being rewritten to look like a published-package test.
