# P7 architecture and evidence review

Final review uses provider `0ac64bc0` and both accepted repair29 applications.
Earlier repair27 and repair28 findings below retain their original scope and
explain the consolidated corrections. Exact final receipts are linked from the
[consolidated review](consolidated-review/README.md).

## Ownership and execution

| Responsibility | Actual owner | Review finding |
|---|---|---|
| Confirmed business/state/rule definitions | Project JSON and discovery history | Peer model registries remain separate from view membership and runtime instances |
| Native execution | Application and its selected native executor | Python uses drive; Node keeps its own observe-mode implementation |
| Probe integration | Managed native adapter plus project-owned `bo_` wiring | Integration receipts compare dependency bytes with the independently installed provider |
| Source discovery | Shared source scope and language adapters | Owned source is scanned independently of existing graph nodes; dependency/output exclusions are classified |
| Behavior correspondence | `behavior/binding_sources.py`, `bindings.py`, `native_runtime.py` | Source bindings, selected values and action completion have separate checks; the observer does not execute permission decisions |
| Per-iteration acceptance | Existing `workflow/change_sync.py` coordinator | `behavior_iteration.py` adds obligations and freshness without a second acceptance authority |
| Capture and recordings | External observer; native capture clients | Fixed-prefix stop and witnessed ancestry preserve actual facts; missing evidence stays a gap |
| Optional analysis | `analysis/` and a bounded TLC child process | Separate JVM, fixed arguments, tool identity, time/heap/output budgets and retained raw results |
| Display | Shared model identities and viewer modules | 2D/3D/Timeline inspect the same definitions and records; view filtering cannot reduce verification scope |

`delivery/integration.py` installs seven Python native files or three JavaScript
native files. It does not copy the viewer or TLC into the application. Project
generators, declarations and observation wiring remain editable application
integration code. The native adapters retain their independent integrity check.

The published source/model snapshots contain no `stategraph-viewer`, `analysis`,
TLC or `node_modules` tree. This inspection concerns the selected archives;
canonical integration and package tests independently check the actual installed
dependency set and observer-free exports.

## Models and source scope

| Accepted snapshot | Mode | State registries | Configured source inputs | Base graph |
|---|---|---|---:|---:|
| Python repair 29 | drive | file, grant, download-job, announcement | 51 | 454 nodes / 1,025 edges |
| Node repair 29 | observe | grant, download_task, announcement, session | 40 | 647 nodes / 1,731 edges |

Counts describe base definitions, not the visible first screen or every expanded
API/project/static-code projection. Source inputs include declarations, tests and
project tooling; they are not all application functions. The source scanner and
engineering view intentionally have different scopes, with the same ownership
inventory underlying both.

Both behavior contracts currently select four state variables and eleven actions.
They do not declare behavior-contract interactions or a finite-analysis profile.
Permissions, transaction order, HTTP responses and cross-model runtime ownership
are tested through their protected concept, mapping and native business gates.
These trial results must not be described as exhaustive exploration of the whole
application. The P3 interaction fixtures and P6 TLC fixtures retain their separate
coverage and provenance.

## Readability and module boundaries

The reviewed modules state their responsibilities in module docstrings. Public
functions document source ownership, input scope and the distinction between a
binding declaration and actual native evidence. `SourceBinding` gives portable
path/symbol identity a frozen record; boundary helpers separate completion,
handoff, shared-read, resource and join obligations.

The design remains compatible with versioned JSON dictionaries. It is not a
fully typed application domain model. Schema and semantic validation happen at
the protocol boundary; internal services still need careful field access and
explicit diagnostics. No typing or total semantic-correctness claim follows from
formatting checks.

The earlier source-quality receipt covers 250 maintained Python modules and 143
JavaScript modules. It is available in
[Node semantic evidence](node-semantic-repair27/source-check.json). The complete
[repair-27 gate](repair-27/results.json) also includes source/binding, integration,
package, native-adapter and analysis fixtures. Formatting is evidence of a common
style, not proof of appropriate architecture; the ownership review above supplies
the complementary source assessment.

## Preservation and remaining decision

The Python provider upgrade retained its accepted source-only refactor, earlier
records and personal settings. The Node semantic iteration retained every one of
568 original field definitions and its reviewed additions. Both used a clean
installed provider; no local framework patch was accepted as product evidence.

A24–A34 now include the complete final Node refactor/provider results, public
dialogue review and the accepted product scene batch. Their scoped decisions
are recorded in the phase ledger and consolidated evidence matrix.

## Subsequent consolidated findings

[Product scenes](product-forest-27/results.json) and the public dialogue export
are now retained. The Node refactor exposed a missing frontend helper dependency;
actual submit/save checks were added to the original command and the repaired UI
passes. Its subsequent burst recording still lost 421 producer events. Final
Node acceptance and the P7 decision remain open; independent desktop checks do
not supersede a capture failure.

[Repair 28](repair-28/README.md) keeps the admission optimization inside the
observer protocol and shared session sink. A request-local declaration index
replaces repeated whole-model scans. There is no new application hook, persistent
cache or execution authority. Per-event schema, provenance and selected values
remain validated, followed by the existing atomic reducer and source checks.
Changing capture definitions or observer exclusions in the next request is still
detected. The measured validation savings do not establish lossless whole-system
throughput; that remaining capacity issue is explicitly tracked.

[Repair 29](repair-29/README.md) keeps further optimization in those same shared
services. The session retains one exact typed serialization and its canonical
model digest. It still reads current source/contract bytes at the existing
admission boundaries. The compiled event validator consumes the same bundled
schema; detailed rejection diagnostics and the minimal-installation fallback
remain in Python. This adds one pinned dependency to the external observer,
without adding application state authority or changing native queue limits.

The installation review also found inconsistent provider selection in project
launchers and the browser bundler. The Skill now requires one selected provider
for generation, checks, startup and optional integrations, with actual path/hash
receipts. Current instructions must follow confirmed business changes while
original dialogue and failed-run evidence remain immutable. Application wiring
correction and native capture now pass on the final installed candidate. The
default npm build/dev runs independently establish selection without provider
environment overrides; actual native recordings and desktop results supplement
the repository tests. The final Node gate checks 73 candidate inputs, including
40 graph-source files. Source-and-model archives and all-input archives make
these different inventories explicit.
