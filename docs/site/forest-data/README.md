# Native trial story data

`initial.json` and `updated.json` are precomputed presentation subsets. They keep
the recording's node IDs, model IDs, declared edges and actual event witnesses.
The independent file, download, announcement and session networks are selectable.
ELK positions the small views during export; browsers do not lay out the full
archive between story sections.

The `.json.gz` files decompress to the original recording bytes. They contain the
captured graph, events, runtime frames and source, and load only for full tools or
source inspection. `manifest.json` records their build identities, hashes and
acceptance references. The full viewer is copied from maintained tool assets;
the static transport cannot run application commands or create new runtime facts.

The initial policy was valid: admission-time authorization permitted an accepted
task to finish. The later user request moved the permission check to preparation
start. Its ordinary run started before revocation and correctly became ready.
The story must not present that sequence as a denied task or as an initial bug.

These are two accepted historical epochs, not two runs on the latest identical
provider: the initial record used `e44cb65f`; the updated record used `66efb5e2`.
Their corresponding native acceptance references are in the manifest. A later
source-only refactor does not rewrite the source captured in either archive.

Rebuild from a reviewed local specification:

```text
node tools/export_forest_demo.mjs <spec.json> docs/site/forest-data
node tools/test_forest_demo.mjs
```

Each specification entry under `epochs` supplies `recording`, `recording_id`,
`build_id` and an `acceptance` reference. The root `dialogue` identifies the
retained, simulated-user trial. Model/recording mismatch and capture gaps fail
export; native acceptance must precede choosing the inputs. Re-exporting data
does not rerun the application or select a more convenient schedule.
