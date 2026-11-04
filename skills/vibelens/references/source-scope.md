# Source scope

Use one project-owned scope for source discovery, project structure, code/API
graphs, source explanations and implementation checks. Scan the application's
code and local modules. Classify installed packages, build outputs, uploads,
recordings and logs before descending into those directories.

## At adoption

Inspect the project tree, package/environment manifests, launch configuration and
`.gitignore`. Identify the backend, frontend, API handlers, models, migrations and
project-owned state/observation adapters. For a new project, record their planned
locations along with the dependency, build and runtime-data locations.

Show a compact path summary. Resolve ambiguous ownership with the user or coding
process, such as whether a `vendor/plugins` directory contains local application
code. Reuse clear project conventions instead of asking a fixed questionnaire.
Directory classification supports the confirmed business graph; it adds no
business rules or application architecture requirement.

`.gitignore` provides evidence about generated or local files. It does not prove
that a file is outside the application's implementation. A local API or model
remains source when a broad ignore pattern matches it.

## Project configuration

Keep the scope in the existing `sync.json`:

```json
{
  "source_scope": {
    "roots": ["."],
    "prune": [
      {
        "path": "third_party",
        "category": "dependency",
        "reason": "Installed application dependencies"
      },
      {
        "path": "var/uploads",
        "category": "artifact",
        "reason": "Uploaded file contents"
      },
      {
        "path": "build-output",
        "category": "artifact",
        "reason": "Compiled frontend output"
      }
    ]
  }
}
```

Full-project stategraph acceptance requires `roots` to contain `"."`, preserving
independent discovery of new top-level source files and directories. Additional
roots can restore specific first-party subtrees. Narrower roots are available
for standalone code inspection; they do not establish complete project coverage.
`prune` entries use exact project-relative file or directory
paths, category `dependency` or `artifact`, and a nonempty reason. Absolute paths,
parent traversal and glob expressions are invalid. Planned output directories
may be declared before they exist; declared source roots must exist.

The shared policy also recognizes standard dependency/cache locations. A normal
directory named `data`, `runtime` or `review` may contain project-owned code;
classify the actual output subtree rather than excluding its whole parent by
name. The standard `review/runtime` evidence subtree is an output location.

An explicit additional source root restores only its own subtree. For example,
`roots: [".", "third_party/local_plugins"]` includes local plugin source while
keeping sibling installed packages outside the scan. Check its declarations and
parameters normally. An override is a source-ownership decision, not a waiver of
mapping or runtime evidence.

Existing `exclude` patterns remain reviewed, soft exclusions. Their code is still
inspected for hidden application implementations and entrypoints. Use classified
`prune` paths for genuine dependencies and outputs; a free-text exclusion cannot
hide an implemented feature.

## During development

Before each coding batch, restore the scope with the project's normal recall.
Review a new top-level directory, dependency/environment change, output-path
change or `.gitignore` edit. Update the same scope when ownership changes, then
run the existing scan/inspect/verify workflow. The inventory hashes `.gitignore`
as an advisory scope input so its changes remain visible.

The source inventory reports encountered pruned prefixes and their reasons. It
does not count unvisited descendants or claim that those files were inspected.
First-party files retain independent discovery, language-adapter errors and
new-file obligations. Source imports resolve against the discovered local units;
installed packages are not recursively added to the graph.

Use the same eligibility decision for project-tree enumeration, AST indexing,
API discovery and source documentation. Physical node `source`/`represents`
bindings, implementation source/parameter references, telemetry registrations and
selected executable files must resolve within that scope. A reference into
pruned storage is a configuration error requiring correction or an explicit
first-party override; it cannot silently become mapped or documented.

Keep hashed inputs separate from executable anchors. `model.source_files` and
`watch_files` can retain configuration, schemas, previous review evidence and
managed-file fingerprints for build identity. Their presence does not make
those files application code or permit a physical execution binding to them.

Preserve existing source, mapping, business and runtime checks. Verify a new local
module is discovered, a dependency/output tree is never traversed, and an
out-of-scope execution binding fails. Source-scope changes must not erase existing
feature or parameter obligations.
