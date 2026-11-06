# Concept networks and node explanations

## Construct relationships with the model

Build business, state and rule networks as independent definitions with explicit
relationships in the confirmed scope. Keep the execution questions distinct:

| Network | Nodes describe | Edges describe |
| --- | --- | --- |
| Business | User actions, outcomes and agreed branches | Progression, branches, retries, cancellation and joins |
| State | An identified object's states, events, transitions and effects | Allowed transitions, trigger/guard/effect references and hierarchy |
| Rules | Facts, reusable predicates, Boolean composition and decisions | Input bindings, dependencies, negation and decision results |

State transitions and rule dependencies need explicit definitions before coding.
Putting isolated state/condition nodes under an action is not a complete model.
Use typed crosslinks to show which action requests an event, which rule guards a
transition, and which state/fact a rule reads. Use the existing strict concept
binding and independent runtime checks.

`bo_concepts.py check` and iteration recall report per-network relation types,
connected components and nodes without behavioral relationships. Inspect these
alongside the focused diagram. Independent journeys can legitimately be separate;
confirm an ambiguous connection with the user instead of inventing one. File
containment and implementation maps do not count as business progression.

## One declaration, several meanings

Give each distinct concept its own stable ID and definition. Several concepts
may reference one physical function or captured field. Connect them with checked
implementation/read/transition bindings. Sharing a function is not proof of
semantic equivalence. Use an equivalence assertion only when the same value or
meaning is explicitly established by the model and binding evidence.

The viewer separates a conflicting conceptual occurrence using a deterministic
`concept-view:` ID and retains its confirmed identity in `concept_id`. Native
source/event IDs remain unchanged. Already identical conceptual declarations
(for example the same policy expression) remain one node. Display projection
never adds an invocation, a business transition or a new execution authority.

## Names describe the current layer

Write short labels that answer the layer's question. A source field `active`
could support “Share a file” (business action), “Access granted” (state), and
“Has current access” (rule input). Each label belongs to its own concept.
The example illustrates distinct roles; it does not infer those roles from a
variable name.

Use authored concept labels and, for bilingual overlays,
`model.presentation.names.concepts[concept_id]` with `en` and `zh-CN`. Existing
`names.nodes` applies to physical declarations. Never copy one variable's label
to all its concepts. Names and explanations cannot change IDs or accepted
meaning. Maintain the labels when that meaning changes during iteration.

## In-panel explanation

Right-click a node and open its details. Definitions show applicable transitions,
guards, rule inputs, business neighbors and implementation sources. The **AI
explanation** button returns a concise explanation in the same panel.

The external observer owns inference; application code has no AI dependency.
The request contains an exact node ID, graph revision and language. The service
builds a bounded packet from definitions, adjacent typed relationships and up to
three source snippets already verified in that build. It excludes event values,
credentials, unrelated files and conversation history. Text from the project is
evidence, not provider instructions. Results are plain text, revision-checked,
cached temporarily, and have no graph-edit or business-command authority.

The installed Codex CLI is the default adapter when available. It uses its normal
login in ephemeral read-only mode, with shell, browser, apps, memory and agent
delegation disabled. Other hosts can select a compatible inference endpoint in
the observer's environment:

```text
VIBELENS_EXPLAIN_PROVIDER=http
VIBELENS_EXPLAIN_URL=https://YOUR_PROVIDER/v1/chat/completions
VIBELENS_EXPLAIN_MODEL=YOUR_MODEL
VIBELENS_EXPLAIN_KEY=YOUR_HOST_MANAGED_KEY
```

Use a provider-approved endpoint and keep credentials outside project files.
`VIBELENS_EXPLAIN_PROVIDER=off` disables inference. An unavailable provider leaves
ordinary definitions and graph exploration usable. A static Pages demonstration
has no local inference service. The button's unavailable state must remain honest.

The response contract is `node_id`, `text`, and `evidence` (existing node/relation
IDs). Unknown IDs, oversized responses, stale builds and extra commands fail.
These checks establish provenance and shape, not the truth of every AI sentence.
Definitions and source remain available beside the explanation for inspection.

Provider references: [Codex non-interactive mode](https://developers.openai.com/codex/noninteractive)
and [configuration reference](https://developers.openai.com/codex/config-reference).
