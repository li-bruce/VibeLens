# Confirm business, state and rules together

Use this reference when adopting VibeLens or changing application behavior. The
three models express the user's current intent and guide the chosen coding
workflow. Each can be inspected on its own; explicit references connect them.

| Model | Define before implementing the affected behavior |
| --- | --- |
| Business | Actors, objects, trigger, actions, outcome and stated alternative paths. |
| State | Object identity, initial state, states, typed events/context, ordered transitions, guards and effects. Include hierarchy, waiting and resource semantics only when they apply. |
| Rules | Typed facts, when they are read, shared predicates, argument bindings, Boolean expressions and operation roots. |

An operation can change state, read it or have no state semantics. A rule may
serve several operations. A lasting business state differs from a function's
entry/return interval. Keep those meanings and identities distinct.

## Discuss a feature

1. Restore existing decisions and the current feature scope. Reuse the explicit
   drive/observe choice. For source adoption, inspect the declared application
   paths rather than dependencies, generated output or runtime storage.
2. Build the applicable business, state and rule definitions in one
   `business-discovery/v2` document. Start from
   [the example](../assets/discovery.concepts.example.json); replace its synthetic
   sources with the real conversation. State and rule drafts need no source code.
3. Ask about meaning-changing gaps. For example, “Does withdrawing this share stop
   the next download?” is relevant when withdrawal is requested. A generic list
   of expiry, approvals and notifications would expand the request.
4. Check the implementation capabilities below before asking to confirm the
   implementation scope. Keep business agreement separate from framework support.
5. Show the affected graph in the conversation and link the verified Web URL.
   Use separate business/state/rule previews when needed. Identify any omitted
   boundary; a partial preview cannot confirm invisible assumptions.
6. Record agreement for the exact semantic scope using the actual answer source.
   A previous answer or direct instruction can already provide that agreement.
   Keep unresolved questions open. Users answer in chat; Web remains a viewer.

`sources`, `decisions` and `changes` retain the existing conversation record.
The additional objects, facts, state models, applicability, expectations and
crosslinks are maintained by the coding agent. Node labels are display text;
business `meaning` and structured model fields carry the confirmed semantics.
Do not rewrite that meaning to match a coding error.

## Check implementation capabilities

Compare the dependency-expanded scope with the installed native binding and
executor before implementation confirmation. The current binding supports one
state model through `primary_state_model` and `model.machine`; a draft can contain
several independent object state models, but binding more than one in the same
scope fails with `unsupported_multiple_bound_state_models`. An engine adapter
alone does not remove that binding limit. Also check required hierarchy,
concurrency and effect semantics against the selected executor.

Preserve the unsupported draft, exact checker input and complete rejection report
under `review/`. Explain the unavailable capability before coding. Continue with
a tested canonical extension or an explicitly agreed scope revision. Keep each
object's identity; silently dropping a model, merging unrelated lifecycles,
excluding required dependencies or weakening checks is not a scope revision.

A revised scope may use one formal state model and independently identified facts,
rules and real observations for other objects. Record the user's agreement and
the retained monitoring requirements. Those facts do not establish complete
transition, guard or effect binding for the other objects. Keep that coverage
boundary visible in delivery results and preserve the earlier draft as evidence.

## Validate, confirm, then bind

```text
python SKILL/scripts/requirements_dialogue.py validate --file discovery.json
python SKILL/scripts/bo_design.py preview --root PROJECT --view state --url ACTUAL_GRAPH_URL
python SKILL/scripts/bo_concepts.py snapshot --root PROJECT --scope CONCEPT_ID
python SKILL/scripts/bo_concepts.py confirm --root PROJECT --scope CONCEPT_ID --sources ANSWER_ID --id CONFIRMATION_ID
python SKILL/scripts/bo_concepts.py check --root PROJECT
```

The snapshot includes semantic dependencies. Confirmation records preserve that
snapshot and its answer provenance; later snapshots do not overwrite earlier
ones. The command checks recorded evidence, not the truth of arbitrary prose.
Do not fabricate a user answer or turn a recommendation into agreement.

Bind the confirmed scope to `model.concepts`, the existing native `model.machine`,
`model.policy`, source nodes, cross-model relations and independent case IDs.
Bindings add implementation detail without replacing the conceptual definitions.
Pending or unsupported bindings fail the implementation gate.

Rule applicability is checked against `binding.business`: each confirmed
operation must resolve to the same native targets named by its bound policy
operation. Reusing a correct rule definition on a different action is a mapping
error. Runtime checks also associate the evaluation with that business invocation.

Every declared transition effect requires an entry in `binding.transition_effects`,
keyed by its canonical transition ID. Each entry names the canonical `effect`,
the native association `edges`, and a `completion` witness:

```json
{
  "effect": "effect:grant:store_grant",
  "edges": ["share-writes-grant"],
  "completion": {
    "node": "grant_transaction",
    "phase": "return",
    "field": "committed",
    "equals": true,
    "identity_field": "transaction_id",
    "boundary": "transaction commit",
    "expectation": "grant-created",
    "path": ["grant", "committed"]
  }
}
```

Use the exact IDs and completion boundary from the project's confirmed model.
The association edges connect the native event operation to every bound effect
operation; an empty list applies only when these are the same native operation.
The witness points to a declared output field and an existing confirmed
expectation that covers the transition/effect, with an independently asserted
case path and expected value. A transaction effect requires its actual
`transaction_id` and `committed: true`. Runtime evidence must link the relevant
invocations and observe that completion for the same transaction. A generic
function return or a source-backed unrelated function cannot replace this proof.
Effects absent from the confirmed model require no invented transaction or node.

Each fact binding identifies its captured `node`, `direction` and `field`.
`basis_checks` point to independent acceptance cases and paths whose expected
value contains that reader and the complete `read_basis`. The observation command
must produce the actual value at the stated boundary. Static binding checks the
connection; the existing runtime/business checks compare the independent result.
Changing a timing label alone cannot establish when a value was read.

```text
python SKILL/scripts/bo_concepts.py check --root PROJECT --model bo_stategraph/project.json --acceptance acceptance.json
```

CLI validation prints a compact result. Use `--full-report` for the assembled
graph or `--out review/concepts.json` to retain the full artifact without sending
it through the conversation. `snapshot` explicitly returns the selected meaning.
Use `review/` for repeatable JSON and Markdown exports. Existing project files
outside the review directories are protected, including unregistered source and
configuration files.

The native application remains authoritative. Drive mode can consume its bound
state declaration; observe mode reads its own implementation. The external
observer does not repeat permission checks, execute transitions or write business
data. Keep state/decision wiring isolated and recognizable in source.

The portable executor has a limited flat-state capability. A valid conceptual
hierarchy is not evidence that this executor supports it. Bind a tested native
adapter or report the unsupported capability. Keep integrated waits, activities,
resource capacities and joins in the existing execution contract. A second Petri
engine is unnecessary.

## Every later coding batch

Inspect the per-layer `networks` report and the affected incoming/outgoing links.
Compare behavioral relationships as well as node coverage: containment alone
cannot establish a business route. Preserve shared rule dependencies and state
transition conditions. Apply [node meaning](node-meaning.md) for separate concept
occurrences, layer-specific names and readable explanations.

For a new empty project, preserve the confirmed design with `bo_concepts` first.
The source-based `change_sync` commands require a parseable project and source
bindings. Establish the first review baseline after that initial scaffold exists,
then run the complete inventory, binding, observation and business checks. This
initial review is not evidence of a prior source diff. Once a baseline exists,
begin every later change before editing, and keep the accepted baseline immutable.

Run `change_sync.py recall` first. It restores confirmed revisions, affected
concepts, shared dependents, pending questions, source/probe obligations and
verification commands. Continue the active change baseline.

Semantic changes include a different transition target/order, guard, rule
operator/argument, fact read timing, object identity or business effect. Show the
changed region and use the matching explicit instruction or answer to confirm it.
Shared rules bring their dependent operations into review. A code move, label
change or equivalent refactor updates bindings and tests without repeating a
settled business question.

Run scan, inspect, verify, accept and check. Keep these results separate:

- Definition legality and recorded confirmation.
- Implementation mapping, source inventory and captured-field coverage.
- Native state constraints and actual transition/evaluation evidence.
- Independent business outcomes and project tests.

Use cases derived from confirmed meaning, including relevant action sequences
and rejection boundaries. Retain independent expectations when fixing code.
Deliberately changing `all` to `any`, dropping a guard or removing a required
source/event should fail the corresponding gate. A finite test suite establishes
the exercised cases; it does not prove every possible execution.

## Existing projects

Version 1 discovery records remain readable with their original checks. They do
not establish the new three-model confirmation contract. Migrate the affected
scope explicitly, preserving IDs, answers and history; never invent agreement
for newly extracted state or rule meanings. Once a version 2 contract is part of
an iteration baseline, downgrading or removing it fails inspection.
