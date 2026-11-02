# Observation continuity during development

## Recall before each coding turn

Run `python observer_runtime/change_sync.py recall --root .` using the project's actual runtime path. Its output restores current mode, active request, requirement IDs, test commands, contract paths and observation wiring. Read affected entries in `.stategraph/observation-plan.json` when changing a layer. These are regenerated summaries of intent, model, implementation inventory and source, not separate requirements to edit.

Keep those authoritative inputs in project version control. The project's normal validation command must include `change_sync check`. Project instructions point to recall and validation commands without activating this Skill in other conversations. A host that supports pre-edit hooks may call recall there; installation alone cannot force every editor to run a prompt.

## Layer obligations

| Layer | Scan | Runtime evidence |
| --- | --- | --- |
| Business | All feature entrypoints and their native sources | Invocation boundaries, selected result and effects |
| States | Executed declaration and state/value bindings | Actual changes and residence; state event and snapshot share the same explicit revision and evidence ID |
| Rules | Shared predicates, arguments and dependency edges | Evaluated, skipped, unknown and exception facts |
| API | Native route registry, decorators and programmatic handler registrations | Real request exit, including redirects and denied/error responses |
| Functions and values | Function signatures, lexical ownership and probe sites | Call identity, entry/return/exception, selected values |
| Data operations | Exporters, ORM/ODM and data-access bindings | Query, transform, commit/rollback and selected result |
| Project structure | Files, folders, imports and dependencies | Projection from current source; no invented calls |
| Code symbols | Static symbols, calls and source mappings | Only explicit source-linked runtime evidence |
| Data structure | Model/schema metadata and relationships | Links to actual operations; no copied application data |

Use stable JSON `source`, `capture`, `lifecycle`, feature `cases` and source-index mappings as machine-readable annotations. Use `bo_` / `BO` for isolated wiring. Extra comments in business code are optional; do not create a second set of IDs there.

Register the actual native `record` and `span` expressions in `sync.json.probe_callees` (for example `bo_probe.record` and `bo_probe.span`). Both Python and JavaScript scanners recognize literal-node spans as entry/return/exception sites. This is static capability evidence; the runtime cases still establish which path executed. Dynamic node IDs remain unresolved until explicitly reconciled.

For an HTTP application, independently compare its native route table with the API projection, including factory-created applications and bound handlers. Python literal `add_url_rule` and `add_api_route` registrations join decorator-derived endpoints. An omitted method stays unspecified because handlers may override framework defaults. Computed paths and unresolved handlers stay explicit gaps; do not rename source into a supported syntax merely to pass. The project tree excludes temporary installation files and never deletes them from disk.

Build HTTP cases from the routes used by the frontend, including HTML form commands, page loaders and downloads. Check their actual framework responses as well as domain calls. An API-only test suite can pass while form submissions lack redirect or error statuses. Record those native comparisons in the existing protected mapping fields/cases; retain them across iterations. Exclude observer and static traffic by identity or explicit route scope, rather than excluding all application routes outside an `/api/` prefix.

## General closure and error-path checks

New integrations set `require_probe_health: true` and `require_observation_closure: true` in `sync.json`. The protected verification contract prevents removing either flag in a later iteration. Each enabled acceptance run must include its complete invocation interval. Live recording may begin/end inside an open call; acceptance cases still cover complete calls.

The verifier audits every explicit `lifecycle: span` even in older integrations. Strict closure also audits legacy `enter`/`return`/`error` pairs and ownership of internal point facts. It rejects missing exits, orphan completions, duplicate entries, missing observation owners and mismatched producer/entity/attempt/call identities. Registered state residence can remain open; it is not a missing function return. A return is an observed boundary, not a business success verdict.

Distinguish native call duration, state residence and a registered conceptual activity. When a business action intentionally spans queued work, bind its actual start/stages/end to that business node's lifecycle and verify those boundaries in a real delayed case. If only a function call is observed, retain its measured duration; never extend it to a later notification based on a label or timestamp. State/activity residence uses run-qualified snapshot instance identity, including when multiple objects share the same request/attempt label. Parallel intervals occupy separate tracks within one layer row. A minimum screen width makes a short call selectable without changing its timing.

Project structure is a filesystem projection available independently of optional AST symbols. Verify ordinary live view and newly saved recording context contain the scoped files, directories and containment links. A recording uses its own captured tree; browsing an old recording must not import today's source as historical evidence. Source additions/deletions update the next projection, while existing node identities and manual layout remain stable.

Recording settlement waits for the queue prefix submitted at the stop boundary, including snapshots. New business traffic may continue beyond that watermark. Preserve submitted/completed/pending counters and actual errors/drops; neither a settled prefix nor a healthy observer proves that an open business operation completed.

Pass the current model when checking invocation closure. Data projections register their native boundaries in each operation's `lifecycle`: a transaction may finish with `commit`, and a transformation with `change` and the captured `transformed` status. Graph activation, Timeline and verification use those bindings. A commit inside an explicit function span does not replace its actual return/exception; arbitrary value changes do not end calls. Missing data exits and wrong call identities still fail. Older data recordings retain their original bytes and use only the adapter's known action/status vocabulary as a compatibility fallback.

Exercise actual denied/error paths and compare response status/fields independently from storage, native results or HTTP. A correct response with missing observation fails mapping. Capture health and closure are separate checks; retain both.

Native test readers must handle absent and inaccessible objects without changing the handler's path. Record a reader failure separately from an application exception. An empty lookup cannot justify an invented object, actor or status; verify the original missing-object response independently.

Bind state changes to actual native authority writes. A notification can report an existing state while only committing a message; that operation is a message effect, not another state transition. Function prefixes and an output named `state` do not establish a mutation. Cover the state-writing operation and notification independently in the mapping cases.

Nested native calls also preserve causal ownership. Use the same probe instance for a request span and its data adapter. Python ContextVar and Node AsyncLocalStorage propagate the current call and selected entity/attempt into actual driver callbacks; transactions become the parent of their body calls. Explicit caller identities still take precedence. Finished or foreign-probe contexts are not inherited. Check parent IDs in real nested and concurrent cases: valid entry/exit pairs alone cannot establish a correct call chain. Add whitebox field assertions on `parent_call_id` for cases that require nesting, and independently compare them to the observed enclosing call. True root calls do not require parents. Do not infer missing historical parents from event timing. Browser runtimes without a native context provider retain explicit `activation.child` scopes.

Python scanning rejects deferred probe `.result(lambda: ...)` callbacks that capture an exception target cleared when its handler exits. Bind selected scalars before leaving the handler. Other dynamic closure problems still need actual executed cases and producer health; static scanning does not establish arbitrary callback correctness.

## Point facts and cross-entity ownership

A rule evaluation, value read or state fact can describe a file while executing inside a request or transaction. Preserve that explicit `entity`/`attempt`. Current Python and Node probes inherit an actual enclosing `parent_event_id` in addition to scoped `parent_call_id`. Both references identify the same witnessed invocation entry. Native adapters retain their own entry ID when adopting a driver callback. Explicit null parent overrides suppress inheritance; span completions retain their original parent rather than themselves.

Complete-run verification checks reference existence, entry type, matching call/project/build/model identity, producer sequence and cycles. With `require_observation_closure`, omitting all ownership fields from an internal fact fails mapping even if its value, business response and invocation exits are correct. A fact can belong to its own already-entered call, an explicit parent entry, or an unambiguous active legacy parent in the same scope. A locally closed parent cannot own a later fact.

An actual `enter` establishes an invocation root. For a native external point notification with no call interval, declare `observation_root: true` on its source-bound node and cover that entrypoint in a real case. Internal rules/values are not external roots. Keep this classification in the existing node definition; there is no parallel root registry or extra acceptance switch. Browser producers without a native context store pass both `parentCallId: activation.callId` and `parentEventId: activation.entryId` explicitly when recording internal points.

The Node data adapter installs the task-local provider. A Node application using
only `bo_runtime.mjs` installs it once in its isolated observation bootstrap:

```js
import { AsyncLocalStorage } from "node:async_hooks";
import { bo_use_context_store } from "./bo_runtime.mjs";
bo_use_context_store(new AsyncLocalStorage());
```

Keep this out of browser bundles. No Promise monkeypatch or global application
state is needed; each probe inherits only its own active invocation.

The live protocol can retain a missing reference as a gap until the entry arrives. Old recordings remain byte-identical. The viewer uses explicit entry references across entities, retaining the old scoped meaning for legacy call IDs. Point facts create no function duration. Unassigned observations are diagnostics of incomplete evidence, not accepted executions; matching timestamps or a sole active request do not supply missing parents.

Verify a real concurrent case containing ordinary `record` and policy facts with explicit file identities. Compare actual root-call concurrency with Timeline invocation bands, not just row counts or entry/exit closure. A passing data-parent check does not establish ownership of rules, states and values.

## Focused values and execution context

Selecting one rule/value node narrows value capture. Current span producers keep
real entry/exit headers for its enclosing calls with `context_only: true` and
`context_boundary: start|end`. The header retains its original ID, phase, time
and parent references, with empty inputs, outputs, basis and dependencies.
Unselected builders and native result summaries do not run. Stop restores normal
capture. Metadata adds no ordinary replay steps and does not establish a business
result. Complete-run verification rejects partial headers as a substitute for
the required full evidence.

Current SDK health reports `boundary_context: true`. The host preserves older
controllers' parent-inclusive contracts when that capability is absent. In the
recording plan, `nodes` retains the display/boundary scope and `value_nodes`
identifies the owners actually sent to the value selector. A remote Node/browser
bridge forwards native health as well as scope and flush operations.

The collector keeps a bounded cache of actual open entries independently of
ordinary history expiry. A focused recording retains only selected values and
their witnessed ancestor boundaries. Deliberately omitted calls are distinct
from missing source events. Cache expiry alone is not a recording gap when the
listener already retained the needed entry. Missing referenced IDs are disclosed
as partial ownership; no parent is inferred from time. Such a partial recording
can be useful for local inspection without claiming complete execution evidence.

## Trial repair order

When an independent trial fails, classify the cause: Skill guidance, shared framework/viewer, or application implementation. Fix general defects in maintained sources and regressions first. Then start a fresh trial with ordinary human requests and natural answers to actual design questions. Do not give instrumentation reminders in routine iterations. Keep each failed run and subsequent repair as evidence.
