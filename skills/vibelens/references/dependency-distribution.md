# Local tool dependencies

The viewer, layout engines, routing libraries and Python observer run from the
installed VibeLens tool. They are not copied into the business project or its
production application. `bo_integrate.py` installs only the native state/probe
adapters: seven small standard-library Python files, or two JavaScript modules.
Project declarations, wiring, tests and private views remain project-owned.

## Setup

The normal Skill and Harness packages contain VibeLens source, licenses and
`assets/stategraph-viewer/dependencies.lock.json`. Third-party viewer bundles
are downloaded when needed:

```sh
python <skill>/scripts/bo_dependencies.py install
python <skill>/scripts/bo_dependencies.py check
```

The source installer prepares them during installation. Generic Skill installers
may only copy files; on explicit activation the Skill runs setup before sharing
the first graph URL. Viewer servers also prepare resources before accepting
traffic. Read-only model queries and disabled Web do not download assets.

For each file, setup uses valid installed bytes, then a verified shared cache.
Missing assets download from the pinned CDN URL first; network failure, partial
content or a wrong checksum triggers the pinned GitHub fallback. SHA-256 and
exact size must match before atomic publication. No downloaded code executes
during setup. App source, project state and personal views are untouched.

The default cache is `%LOCALAPPDATA%/VibeLens/dependencies` on Windows and
`~/.cache/VibeLens/dependencies` elsewhere. Set `VIBELENS_DEPENDENCY_CACHE` or
`--cache PATH` to choose another location. `--source github` selects the fallback
directly when a network blocks the CDN. Setup uses four bounded download workers.

## Offline use and recovery

- Existing verified assets require no network. `install --offline` may also
  restore missing files from a populated cache.
- For a disconnected computer, use `vibelens-offline-vVERSION.zip` from the
  release. It includes the same source plus dependencies and corresponding source.
- If both sources fail, setup exits with the failed filename and source errors.
  Resolve connectivity or install the offline package before opening the graph.
- A locally modified dependency is preserved and reported. `install --repair`
  explicitly restores only locked dependency files; `check` never changes files.

For source checkout, run `python tools/setup_viewer.py` before direct Node tests.
It restores dependencies for the canonical viewer and historical full-copy
examples. Normal verification and Pages builds call it automatically. Build the
small packages with `python tools/build_distribution.py`; add `--offline` to
produce the complete optional ZIP. Build tools and npm lockfiles remain in
`tools/routing` and `tools/spatial` for reviewed dependency changes.

## License and source

Original VibeLens code uses MIT. Downloaded libraries retain their terms:
libavoid-js uses LGPL-2.1-or-later; ELK uses EPL-2.0. Local debugging and
download-on-use do not change those licenses. Commercial application development
is not prohibited by VibeLens. Notices remain in source and every package.

`libavoid-sources.zip` is also a pinned download beside the viewer, included in
the offline package. See [source provenance and replacement](vendor/README.md).
The Wasm matches the reviewed upstream bytes; a byte-identical native rebuild
remains unconfirmed. These delivery changes do not change that evidence.

All download URLs fix an npm version or the full retained Git commit
`2f0833810969087df6a05f58c5bd876a72f5e85d`. No URL tracks a moving branch or `latest`.
That commit remains the GitHub fallback for these reviewed dependency bytes;
dependency updates require new pins and validation.
