# Repair 18 — SQLite collection alongside atomic publication

P7 remains in progress. This repair addresses a framework interference found in
the Node observe trial; it does not complete its browser acceptance or either
trial's remaining business iteration and source refactor.

## Failure and diagnosis

The unchanged Node SQL.js store commits an in-memory transaction, exports a
complete SQLite image to a sibling temporary file, then calls `renameSync`.
During the actual browser run, replacement failed with EPERM and the worker
process exited. The second recording stopped through exception cleanup.
The first recording had stopped normally; neither was rewritten.

`node-original/` retains the native failure, original recordings and OS-backed
diagnosis. A barrier inside the real canonical SQLAlchemy collector reproduced
the conflict with the unchanged native `Store.persist`: replacement failed while
the SQLite connection was open and succeeded after normal disposal, with the
reader process still alive. This proves a sufficient configured conflict, not
the identity of the holder at the historical crash instant; that instant has no
handle snapshot.

The complete original bundles remain local. Repository review copies omit the
collector credential and raw databases; their manifests identify each excluded
member and the original archive hash. Included event and diagnostic members are
byte-identical. No historical evidence was overwritten.

## Shared repair

- `sqlite_file_mode` records the actual persistence mechanism in the strict store
  declaration. Transactional collection remains the default.
- Explicit `atomic_replace` publishers use `data/sqlite_snapshot.py`. On Windows,
  a private same-volume hard link pins one complete published image. The reader
  opens that alias, releases it before reflection, and uses query-only SQLite in
  memory with the existing SQLAlchemy Inspector. The next poll sees a later
  published schema. Ordinary transactions and WAL keep the existing collector.
- File identity, schema constraints, catalog validation, observation exclusion,
  source freshness and runtime evidence checks remain active. The observer does
  not modify native application persistence or substitute declarations for the
  real database catalog.
- Coding guidance derives the mode from documented source and requires actual
  collector-on/off write checks. Persistence changes require the same review.

The snapshot path is deliberately bounded: at most 128 MiB per image, standard
SQLite/pysqlite, no extra URL options, no WAL/journal sidecars. Windows requires
a writable same-volume temporary directory with hard-link support. The image
contains data pages temporarily in process memory; only schema metadata is
exported. The private link is deleted on handle close. A failed precondition is
reported, retaining the last good catalog as stale; there is no live-file fallback.

## Failed fix retained

The first implementation opened the original path with `FILE_SHARE_DELETE`.
That still blocked replacement on this Windows host. Both sandbox and host
failures are retained in `first-retest.log` and `host-retest.log`. The isolated
`windows-sharing-probe.json` compares original-name and hard-link reads. The
final regression holds the actual private read handle and the reflection stage
while replacing the original file; it also checks cleanup, schema changes,
constraints, bounds, invalid modes and default transactional WAL collection.

## Evidence

- `baseline-failure.log`: new regression against the preceding implementation.
- `alias-retest.log`: first successful hard-link regression (11 cases).
- `database.log`: expanded final database suite, including 13 snapshot cases.
- `source.json`: maintained-source syntax, lint and formatting checks.
- `installation.json`: independently installed maintained-file byte comparison.
- `native-probe/`: the isolated Node trial uses that fresh installation and its
  unchanged `Store.persist`. Publication passes with both the actual snapshot
  read handle and reflection held at a barrier; old-image consistency and next-
  poll discovery of a new table pass. These two probes are not a full browser run.
- Managed-example, full-run and clean-export receipts are listed in `results.json`
  after those gates finish. Pending native trial runs stay separate.

Relevant platform contracts: [SQLAlchemy reflection](https://docs.sqlalchemy.org/en/20/core/reflection.html),
[SQLite backup semantics](https://www.sqlite.org/backup.html),
[Windows file replacement](https://learn.microsoft.com/en-us/windows/win32/fileio/moving-and-replacing-files).
The held-handle behavior above is established by the local reproductions, not
inferred solely from the platform documentation.
