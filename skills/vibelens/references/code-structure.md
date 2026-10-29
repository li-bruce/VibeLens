# Optional code structure

## Engineering tree and code symbols

The **Project structure** view ends at directories/files and named dependency
boundaries. The **Code structure** view continues through classes, functions and
declared parameters. Both are projections of the same source index and share IDs
with focused code neighborhoods. The project tree is scanned after coding; it is
not a model that the AI must design or maintain by hand.

The engineering layer uses `code_role: directory|file`, `project_path`, and one
physical `parent`. `code-contains` is containment; `code-imports` and
`code-exports` retain literal module references and source locations.
`code-dependency` comes from direct `package.json` or PEP 621 `pyproject.toml`
declarations. Explicit `workspace:`, `file:` and `link:` dependencies resolve to
in-scope manifest files; matching a package name alone is insufficient. Other
names remain boundary nodes. `code-links` represents filesystem links to
in-scope entries, without recursively following them. `code-defines` connects
files to the existing code-symbol layer. Static edges do not claim execution.

The tree includes empty directories and non-code files under the declared
`source_scope.roots`, respects explicit exclusions, and prunes dependency/cache
trees. Observer view preferences do not invalidate its revision. Existing source
coverage checks still reject hidden implementations and unsupported adapters.
File/folder IDs survive content edits; moves create new path identities. Existing
layout migration handles explicit ID aliases, without guessing that identical
files are renames.

File dependency counts and strongly connected components are static metrics.
Folded regions retain underlying file-edge members. They do not establish
whether the project violates its architecture; that requires explicit boundaries.

```bash
python SKILL/scripts/bo_code.py query --root PROJECT --projection project --limit 400 --out review/project-tree.json
```

The same projection is available at `/api/code/graph?projection=project`.
Full scans export `project.entries`, `project.file_cycles` and scope exclusions;
bounded queries report omitted project entries and cycles explicitly.
The live file reader remains revision-bound and exposes indexed source, HTML,
CSS, SQL and supported package manifests. Other files remain structural entries.

Current dependency resolution covers Python syntax and literal JS/TS/React/Vue
imports/re-exports, including relative resource imports. Unresolved aliases stay
unresolved. HTML/CSS reference extraction, arbitrary build-tool configuration and
transitive lockfile dependency analysis are not implemented.

Use the existing source adapters and viewer. Keep business labels and runtime
state in the authored model; source-derived declarations are a separate projection
within the same graph. The feature is available in both drive and observe modes.

The default overview stays compact. Tell the developer they can select a region
and enable **Local code**, or choose **Code structure** for the full indexed scope.
Both use the same dragging, expansion, notes, source navigation and filters.
Static nodes are not recorded business operations.

```bash
python SKILL/scripts/bo_code.py scan --root PROJECT --out .stategraph/code-export.json
python SKILL/scripts/bo_code.py query --root PROJECT --focus NODE_ID --depth 1 --out review/code-focus.json
python SKILL/scripts/bo_code.py check --root PROJECT
```

Use the project's reviewed `sync.json` source scope. Missing parsers, unsupported
languages, syntax failures and excluded implementation must remain visible gaps.
Do not restrict the index to nodes that already exist in the business graph.
Do not identify functions by line numbers or infer ambiguous targets by labels.

Once enabled, `.stategraph/code-graph.json` is refreshed by viewer requests and
`bo_sync scan/watch`. Run maintenance after coding and before verification. The
verification command independently checks the current source against this export;
it must fail if declarations, relations or file coverage have drifted. Preserve
the failed check before refreshing and retesting. Source code edits do not imply
that a native application has reloaded; keep its build status distinct.

During each relevant batch, verify the changed feature from its business node
through its source binding and actual runtime evidence. For source changes, cover
new/deleted declarations, call direction, parameter changes and unresolved targets.
Exercise focused and complete views, boundary relations, saved layout/notes and
source revision checks. Verify opening/refreshing/filtering the code view produces
no business events. Keep runtime and business checks independent of static edges.

The supported relationship index covers files, classes, functions, declared
parameters, imports, inheritance and syntactic call occurrences in Python,
JS/TS/React/Vue. It does not prove dynamic dispatch or arbitrary variable flow.
Bounded queries report omitted content; use JSON export for the full indexed
scope. Never describe a bounded canvas as every possible execution path.

## API entries and layers

Literal route registrations recognized by the Python and JavaScript adapters appear
as **API** nodes linked to their handler declarations in **API entries**, **Code structure**, or a matching **Local code** region. The optional Layers control
can separate these entries from business actions, states, rules, functions/values,
data structure and source declarations. Local code includes registered callers of
the selected handler. The complete code view also retains authored source bindings.

These are source registrations, not recorded requests. Dynamic route construction,
framework prefixes and middleware dispatch need explicit application bindings and
real request tests; never guess a full URL or imply an endpoint was exercised.
Observer routes stay excluded from application endpoint nodes. Keep function,
method and parameter containment; a parameter belongs to its declaration, while a
captured event field belongs to its collecting operation. Verify those separately.

Source opens the complete file on demand, with line numbers and automatic focus.
Parser-supplied UTF-16 ranges highlight a declared parameter precisely, including
non-ASCII names and Vue script offsets. Files are cached by bound source revision
inside the viewer; graph JSON carries locations rather than complete source files.
Opening another parameter in the same version reuses that file. Changed revisions
invalidate the source cache. Captured adapter fields locate their collection owner;
a missing source-variable binding must not be replaced with a guessed text match.
