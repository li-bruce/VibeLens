# Layer necessity and modeling boundaries

Baseline: `main`, `3a43294d84d38bda4bcd7670a0b67e9985fa3ed5`.

The later implementation and retained verification are recorded in the
[concept-model acceptance report](../../review/concept-models-20261104/README.md).
This assessment remains the original baseline analysis.

This assessment reads the maintained model, source projections, viewer and retained examples. It also executes one read-only inventory projection. It does not rerun application acceptance, change the layer implementation or publish a new version. Recommendations below describe proposed changes, not implemented features.

The follow-up [model-first proposal](../../development/concept-model-first.md) makes the three peer business/state/rule models explicit, audits their current pre-code support and specifies confirmation, binding and iteration gates. Simpler default navigation must not remove their independent conceptual views or development role.

## Finding

The nine current display planes do not form nine successive levels of abstraction. They combine semantic concerns, source granularity, implementation roles and observation selection. This explains part of the duplication and visual load. Reducing the number of planes is reasonable; deleting the underlying state, rule, source or runtime facts would lose useful behavior.

The strongest consolidation is to unite core functions and code symbols under one implementation view. Project structure becomes its coarse-grained navigation. Data operations retain their evidence but become an operation role and an optional data-access view. Business actions and states can share the default behavior view while keeping different formal meanings and a dedicated state-machine preset.

## Engineering criteria

A useful independent model or view answers a distinct question, has identifiable entities and relation semantics, and is supported by a declaration, source fact or runtime observation. A category is not an independent abstraction merely because it has a color or collector. Ask what information would be lost if it became a subtype, filter, property or detail of another view.

Architecture viewpoints and model kinds are established concepts; ISO 42010 does not prescribe this project's nine planes or a development method. C4 explicitly separates static zoom levels from supporting dynamic/deployment diagrams, and recommends only the detail that helps the audience. Its code-level diagram is optional and can show selected important methods. Those principles support multiple views and progressive disclosure, rather than one mandatory vertical staircase. This is an application of those ideas, not a claim that VibeLens implements C4 or conforms to ISO 42010. [ISO 42010 abstract](https://www.iso.org/standard/74393.html), [C4 diagrams](https://c4model.com/diagrams), [code detail](https://c4model.com/diagrams/code).

Keep these dimensions distinct:

| Dimension | Example | Consequence |
| --- | --- | --- |
| Semantic model | Business action, state, permission decision | Different questions, not necessarily increasing detail. |
| Structural granularity | Package, file, class, function, parameter | Coarse/fine navigation within implementation structure. |
| Role or selection | Core, observed, HTTP entry, database access | Usually a filter or facet, not another function identity. |
| Runtime occurrence | One invocation, one rule evaluation, one state residency interval | Evidence referring to definitions; not another static layer. |
| Presentation | Plane, region, preset, collapsed neighborhood | A view over facts; it must not redefine those facts. |

## Each current layer

Current IDs and their mutually exclusive classification come from [graph-layers.js](../../../skills/vibelens/assets/stategraph-viewer/graph-layers.js#L4). Recommendations concern default presentation unless a model change is stated explicitly.

| Current layer | Actual content and useful question | Critical assessment | Recommendation |
| --- | --- | --- | --- |
| Business (`business`) | Confirmed actions and their user-relevant relationships. What does this feature do? | Essential to this product's purpose. It must not become a list of HTTP requests or every function call. A business operation can span several functions or services. | Retain as the default entry. Link its implementation explicitly; do not manufacture wrapper functions solely to obtain one source anchor. |
| States (`state`) | Native state values, transitions, hierarchy, waiting and semantic state parameters. What can change, and which states are active? | Formal state semantics are essential. A state and an action are different entities, but they need not occupy permanently separate planes. Call waiting and business waiting are not automatically the same state. | Co-display business actions and relevant states in a behavior view; keep the exact machine contract and an optional machine-only view. |
| Rules (`rules`) | Decisions and resources. Which inputs and conditions determine permission or readiness? | A shared decision model has independent semantics. Current classification also places capacity resources and joins here; that is broader than permission or shared-policy DAGs. | Retain the rule model; make its detailed plane/view conditional. Keep capacity, synchronization and permission roles distinct. Small guards can stay near the action/transition they constrain. |
| API (`api`) | Registered methods/routes and handler mappings. Where does execution enter? | A route is not its handler. Several routes can legitimately share one function. The same concern also occurs at CLI, UI callback and message-consumer entry points. HTTP is a specialized implementation boundary, not a universal abstraction level. | Retain interface identities and runtime qualification. Make API an entrypoint facet and focused preset within implementation; expose a separate plane when it helps a networked project. |
| Functions and values (`execution`) | Authored observation anchors, selected values, effects and fallback-classified nodes. What was selected for observation? | A core function is still a function. Selection, importance and capture origin do not establish a second source declaration. Collected event fields are not necessarily lexical parameters. | Remove this as a competing general source layer. Merge physical functions into the implementation view; keep core/observed filters. Preserve distinct operation/capture identities where they represent genuinely different objects. |
| Project structure (`project`) | Directories, files, imports and manifest dependency boundaries. Where is the code organized? | Valuable for navigation and dependency review, but it is the coarse grain of the same implementation structure. Folder containment alone is not a component architecture or proof of excessive coupling. | Retain the scanner and project-tree preset; combine it with symbol drill-down. Architecture violations require declared boundaries, beyond import counts or cycles alone. |
| Code symbols (`code`) | Classes, functions, parameters, syntactic calls and additional source-anchored helpers. Which declarations implement this part? | Needed as the physical implementation base, but not every indexed symbol must be displayed. Context-generated helpers currently coexist with the canonical index and can resemble duplicate declarations. Static calls are not proven runtime dispatch or arbitrary value flow. | Retain as the unified implementation graph. Use file/class/function/parameter detail levels and local code expansion. Share one physical declaration identity and use view references for context appearances. |
| Data operations (`operations`) | Reads, writes, queries, transactions, transformations and their capture fields. What was accessed, returned or committed? | The facts are useful, but this category mixes native I/O, transaction boundaries, arbitrary transformations and JSON fields. A separate permanent plane is not required. An ordinary transformation function is still implementation; an actual transaction/query can be a distinct runtime operation. | Remove the mandatory general plane, not the collectors or evidence. Put native operation types in the implementation/runtime model; provide a data-access preset combining operations, callers and target schema. Keep explicit nodes for useful multi-query, transaction or pipeline detail. |
| Data structure (`data`) | Databases, tables/collections, fields and declared/observed constraints. What structure is stored? | Independent structural information that neither function signatures nor a directory tree fully expresses. It is not intrinsically below source code. Current catalogs do not amount to a complete domain-object/type model. | Retain conditionally as storage/schema structure. Show it beside relevant operations. Distinguish domain classes, DTOs, ORM declarations and physical storage through mappings; do not invent a database layer for projects without one. |

These are not recommendations to require a replacement fixed number of planes. Different projects and tasks need different selections. A small pure frontend may need behavior and implementation only; a database-heavy application benefits from storage and access views; a complex policy system benefits from a focused decision view.

## Specific verified problems

### Different concepts share one classification switch

[layerOf](../../../skills/vibelens/assets/stategraph-viewer/graph-layers.js#L45) prioritizes query/transform ownership, capture roles, source roles and semantic types, then defaults to execution. [nodeType/viewTypes](../../../skills/vibelens/assets/stategraph-viewer/graph-core.js#L616) separately assign visual type and overlapping filter membership. A source-bound resource can therefore occupy the rules plane and participate in a function view. This does not create another execution, but the current vocabulary makes those distinctions hard to understand. Unknown or conflicting classifications should be diagnosable rather than silently interpreted as ordinary functions.

### Source declarations, observation definitions and occurrences are conflated in presentation

[code_structure.py](../../../skills/vibelens/scripts/bo_observer/graph/code_structure.py#L350) keys helper generation by business group and source symbol. Its `code.*` helper receives a caller parent. The independent [code index](../../../skills/vibelens/scripts/bo_observer/code_graph/index.py#L18) has another physical symbol identity. The delivery model maps `app/service.py::authorized` to a business anchor, a decision anchor and three source helper nodes. The first two may express different legitimate meanings; the three helpers should be identifiable as context appearances of the same declaration rather than three independent functions.

Unifying views must preserve these distinctions:

- One physical source declaration, identified by project, normalized path, qualified symbol and declaration role.
- A semantic business operation or rule, which can map to one or several declarations.
- An observation definition or capture point, with selected fields and an explicit source binding.
- Each actual invocation, with its own call/span identity and causal relationships.

Use stable alias/reference mappings for existing IDs and recordings. Do not merge by names, comments, proximity or shared source alone. Two different routes are not duplicates merely because their handler is the same. An operation spanning several functions is not equivalent to one of those functions.

The converse matters too: several valid observation definitions may bind the same function. In the file-sharing example, `upload`, `db_metadata`, `db_upload_tx` and `db_insert_file` bind `SharingService.upload` but describe the overall action, a transformation, a transaction and a write. Their source declaration can be unified while their operation and invocation identities remain distinct. See [the actual function](../../../examples/file-sharing/app/service.py#L67), [transformation capture](../../../skills/vibelens/scripts/bo_observer/data/runtime.py#L488) and [transaction capture](../../../skills/vibelens/scripts/bo_observer/data/runtime.py#L546).

API registration identity also needs qualification. [Endpoint identity](../../../skills/vibelens/scripts/bo_observer/code_graph/index.py#L201) currently includes handler, path and methods, while [registration identity](../../../skills/vibelens/scripts/bo_observer/code_graph/endpoints.py#L48) also includes receiver and declaration position. [Observation qualification](../../../skills/vibelens/scripts/bo_observer/code_graph/observation.py#L64) can reject ambiguous registrations. Do not assume that all receiver-specific registrations already have distinct static endpoint entities, or collapse registration and observed request identities during this consolidation.

### Generated field nodes dominate an example inventory

The read-only [inventory evidence](inventory.json) uses the retained `examples/file-sharing/bo_stategraph/project.json`. Its 123 authored/managed nodes expand to 441 inventory entries. Of the 241 entries classified as data operations, 229 are generated capture fields; execution has 101 entries, including 89 fields.

This is the base inventory before default advanced filtering or collapse. It includes no separate code/API/project snapshots and no actual events. It does not mean that the default canvas displays 441 entries, that 241 database operations occurred, or that API/project support is absent.

[capture-fields.js](../../../skills/vibelens/assets/stategraph-viewer/capture-fields.js#L3) explicitly describes these as recorded JSON fields, and retains owner/direction/path. Most can be inspected as selected values or structured detail on their owner. Promote a field to a graph node when it participates in a useful relationship, is a tracked state/decision input, or the developer explicitly selects it. A field with no lexical binding must not masquerade as a function argument or a source-highlight target.

### Data operations have evidence, but the type is too broad

[data/projection.py](../../../skills/vibelens/scripts/bo_observer/data/projection.py#L265) emits all managed operations as `kind: function` and labels every non-transform action `data_role: query`, including transactions. [data/protocol.py](../../../skills/vibelens/scripts/bo_observer/data/protocol.py#L196) retains the more precise action and capture requirements. The underlying evidence can distinguish query targets, rows, transaction identity/commit and selected transformation values; the broad visual classification obscures it.

OpenTelemetry likewise represents a database client operation with operation and target attributes, duration and response evidence. It does not require a separate database-operation drawing plane. A query returning is also not the same fact as a transaction committing. [Database semantic conventions](https://opentelemetry.io/docs/specs/semconv/db/database-spans/).

Data lineage is a further concern: OpenLineage distinguishes Job and Dataset design facts from a Run occurrence. Query observation and schema introspection alone do not prove complete column or row lineage. Current selected before/after values should not be advertised as exhaustive data provenance. [OpenLineage object model](https://openlineage.io/docs/spec/object-model/).

### One parent field carries incompatible meanings

The model checks one [acyclic parent chain](../../../skills/vibelens/scripts/bo_contracts.py#L518). Machine projection then assigns [state hierarchy to parent](../../../skills/vibelens/assets/stategraph-viewer/machine-projection.js#L67). Source helpers use the caller as parent, while project symbols use lexical/file ownership. These are business decomposition, state containment, static call context and physical containment, respectively; none establishes actual runtime call parentage on its own.

Keep distinct relationship meanings for file containment, symbol definition, business implementation, state hierarchy, decision dependency, runtime parentage and view membership. A display group can reference one physical element in multiple contexts. The relation graph as a whole need not be a DAG or a single tree; a rule expression DAG and a directory tree have narrower invariants.

### Folding or hiding a plane does not yet preserve hidden paths

[layerSlice](../../../skills/vibelens/assets/stategraph-viewer/graph-layers.js#L145) removes edges whose endpoints are no longer visible. It does not calculate a witnessed connection through hidden intermediate layers. The [existing projection proposal](../../development/dynamic-layer-projection.md) explicitly remains unimplemented. Consolidating layer controls must therefore include a separate typed view-projection plan. A displayed indirect relationship must retain its original path and must not imply a direct call, authorization, transition or observed execution.

## What must remain separate even if it is shown together

Business actions describe what someone does; states describe a lasting condition and legal transitions. The [state contract](../../../skills/vibelens/scripts/bo_contracts.py#L567) validates declared values, transitions, guards and equality with the runtime declaration. [Machine projection](../../../skills/vibelens/assets/stategraph-viewer/machine-projection.js#L50) actually materializes states and transitions. A combined behavior view must preserve those checks and types. Formal statecharts explicitly model hierarchy and parallel state configurations; a function-call diagram cannot replace that semantics. [W3C SCXML](https://www.w3.org/TR/scxml/).

Rules answer why a decision is permitted. They can be reused across actions and state transitions. The current [shared-policy projection](../../../skills/vibelens/scripts/bo_observer/policy/projection.py#L109) already attaches them to business operations. DMN likewise treats decision models as complementary to process models, supporting independent decision semantics without requiring every guard to occupy a permanent plane. VibeLens's current typed expression DAG is not a complete recursive ReBAC engine; source predicates still evaluate project relations. [OMG DMN](https://www.omg.org/dmn/).

Runtime lifecycle belongs across views. [Lifecycle resolution](../../../skills/vibelens/scripts/bo_observer/observation/lifecycle.py#L44) reads registered bindings or neutral entry/wait/return/exception evidence. Business state residency, rule evaluation, a native query and a function invocation can each have appropriate temporal facts. Static folders and unobserved source functions do not acquire lifetimes from their children. OpenTelemetry spans describe particular units of work with timestamps and causal identity; those facts should attach to the relevant model and source objects. [OpenTelemetry traces](https://opentelemetry.io/docs/concepts/signals/traces/).

Current rendering modes share the layer classifier, but their evidence capabilities are not identical across all layers. Historical replay uses saved project/API snapshots when available, and the current optional Code view is disabled there rather than inserting today's source into an older recording. Preserve that isolation when combining views. A populated static source plane is not proof that every function was recorded or has a Timeline duration.

Finally, an enum state is not identical to the variable holding it. Current [representation links](../../../skills/vibelens/scripts/bo_observer/code_graph/query.py#L8) enforce exact semantic-parameter to source-parameter mappings and explicitly reject that interpretation. Implementation, representation, derivation and equality must not collapse into a generic cross-layer link.

## Recommended presentation and engineering sequence

Use three common navigation entries over the same network:

1. Behavior: business actions with relevant states and concise guards; expand the exact state machine or shared rule network when needed.
2. Implementation: entry points, modules/files, classes/functions and selected values. Start with observed/core elements; drill into the physical index. Project, API, function and local-code presets select different scopes or grains of this same implementation.
3. Data: native schema beside witnessed access and transformation detail. It is conditional, not a required bottom floor.

Rules, interfaces and data access remain valuable focused presets. Runtime instances, observed values and Timeline are synchronized evidence over these views, not a second copy of every source symbol. Spatial planes remain available for chosen combinations; the vertical order is a layout choice, not a proof of abstraction.

Before changing controls or colors:

1. Specify entity kinds, source/capture/occurrence identities and typed relations. Keep compatibility aliases and historical evidence.
2. Unify classification metadata across graph filtering, renderers, legends and Timeline. Separate core/observed and entry/I/O roles from entity identity.
3. Consolidate source projections and add explicit context references. Distinguish query, transaction, ordinary transformation and observed field.
4. Reduce default field nodes and provide deliberate local expansion; retain capture/export and strict source bindings.
5. Change presets and optional plane composition, including the missing typed hidden-path projection.
6. Recheck source uniqueness, action/state/rule differences, exact route/handler identity, capture-field provenance, query-return versus commit, and 2D/3D/Timeline consistency. Preserve source/mapping/business checks independently; a lower plane count must not relax coverage.

The current native state executor and independent observation module remain intact under this recommendation. The proposed consolidation changes how developers navigate and how projections identify facts, not whether program behavior is observed or strictly checked.
