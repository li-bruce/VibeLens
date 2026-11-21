# Node: current provider, static checks

The trial selected the immutable repair-24 installation through the managed
plan/apply/check flow. Its 464 owned files match commit `24af640d`; the native SDK
files and application declarations are unchanged. Current candidate:
`1ebc6e635cf03e4a78cbe297d6b15cb19bd7531e7d8a22c348f04ec8b6db35c5`.

Source, SQL, raw recordings, personal settings and the previous handoff were
preserved. The normal inspection refreshed one derived source-index cache; its
original diagnostic and independent recomputation are retained.

[The original handoff](HANDOFF.md) lists the exact checks and remaining work.
[Original receipts](receipts.zip) contain 39 files, verified against their
[original seal](original-seal.json). This handoff does not include a database
migration, native run, browser run or acceptance.
