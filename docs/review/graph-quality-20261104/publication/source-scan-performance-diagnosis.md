# Read-only source-scan performance diagnosis

No source, native acceptance process, project evidence or application data was
modified by this diagnosis. Profiling calls use canonical `CodeGraph` with
`persist=False`; they do not run business functions or database queries.
Measurements were taken on Windows during other acceptance activity, with
cProfile overhead. They are diagnostic samples rather than isolated benchmarks.

## Measured facts

| Scope | Cold | Same object, warm | API endpoints |
| --- | --- | --- | --- |
| Maintained archive project | 62.82 s | 62.58 s | 0 |
| Current source of the project served on port 50958 | 7.57 s | 5.46 s | 4 |

Receipts retain cumulative function timings:
[archive cold](archive-api-cold-same-instance-02.json),
[archive warm](archive-api-warm_same_instance-same-instance-02.json),
[live-project cold](old-live-api-cold-profile-01.json),
[live-project warm](old-live-api-warm_same_instance-profile-01.json).
Both pairs retained identical revisions and no API errors.

The archive warm call spends 61.91 of 62.58 seconds in `source_inventory`.
`source_paths` accounts for 43.41 seconds, including 34,531 `os.walk` calls and
about 36,700 filesystem stat calls. An earlier cold sample separately measured
12.11 seconds in `scandir`, 14.97 seconds in stat and 9.60 seconds checking path
links. Parsing was about 2.89 seconds in that sample. A minimal API response
therefore does not imply minimal work before producing it.

The [directory-only inventory](archive-scope-directory-count-01.json) found
34,530 directories after the existing global exclusions. Of these, 34,502 are
under `review`; `review/runtime` alone has 34,473 immediate UUID directories.
The dominant walk is retained runtime scenario artifacts. This is not evidence
of `.release` recursion: `source_paths` already prunes `.release`, `.stategraph`
and `.validation` before descent, and the architecture guard's configured scan
roots do not include `.release`.

A separate read-only HTTP request to the existing observer returned 200 in
4.89 seconds with a 1,133,003-byte response, zero events, 244 model nodes and four
API nodes: [HTTP sample](live-view-timing-01.json). Existing browser polling and
other activity were present, so this does not isolate HTTP latency from service
contention. The same project's standalone canonical API profile demonstrates
that source refresh itself is a significant contributor.

## Code paths and limits

- `bo_observer/workflow/bo_sync.py:60` implements the directory walk. Global
  ignored names are pruned early. Ordinary exclusions such as `review/**` are
  deliberately inspected for hidden implementations and entrypoints.
- `CodeGraph.refresh()` calls `source_inventory()` on every invocation, before
  comparing the source fingerprint. The cached graph therefore does not avoid
  the warm filesystem walk. `api_snapshot()` filters endpoints only after this
  refresh; the optional full graph is built when its fingerprint changes.
- `change_sync.inspect()` takes a snapshot, performs structural checks and
  calls `maintenance_task()`. When the optional code cache exists, maintenance
  refreshes it and inventories source again. `verify()` adds a fresh independent
  code/API check. `accept` and `check` call inspection again. Multiple complete
  inventories explain substantial repeated work, though these profiles do not
  quantify every stage's share of native acceptance duration.
- The archive code cache currently has 713 nodes and 974 edges from seven source
  files, with 296 excluded paths. It does not contain 34,000 source directories.

## Safe next changes to evaluate

1. Replace redundant `os.walk` plus `Path.lstat`/path-link checks with a short-lived
   `DirEntry`-based walker. Keep the same roots, global exclusions, regular-file
   selection, symlink/junction behavior and explicit excluded-source inspection.
   Current [Python documentation](https://docs.python.org/3.11/library/os.html#os.DirEntry.stat)
   explains that Windows `DirEntry.stat(follow_symlinks=False)` can use enumeration
   metadata without another syscall. Compare complete inventories and add
   link/replacement, new/deleted source, exclusions and error regressions before
   calling the implementation equivalent. This still visits every directory;
   the size of any benefit requires measurement.
2. Evaluate reuse of the existing content-hash-validated Python inspection cache
   in `CodeGraph.refresh`, as already done by `project_view`. Current bytes and
   new files must still be examined, and parser identity changes must invalidate
   cached inspection facts. This can reduce repeated AST work, not eliminate the
   directory walk.
3. Treat any longer-lived source index or background refresh as a separate
   design requiring explicit revision/staleness handling and complete new-file
   discovery. Do not skip refresh just because the previous graph had no APIs.

Simply pruning `review/runtime` using the existing broad exclusion would remove
the current hidden-endpoint inspection guarantee. It is not an equivalent repair.
No new ignore rule, cached file-byte authority or reduced acceptance check is
proposed here. A before/after baseline is still needed to attribute the entire
native workflow slowdown to a specific framework version.
