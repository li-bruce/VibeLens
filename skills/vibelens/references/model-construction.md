# Construct and review the requested models

Use this during initial design and each affected feature iteration. The result is
the application's business networks, object state models and shared rule networks,
with their actual relationships. A questionnaire alone does not produce that result.

## One construction record

Use `business-discovery/v3` for new construction. Retain existing `networks`,
`objects`, `state_models`, `policy`, typed crosslinks and confirmations. Existing
projects migrate with `bo_upgrade.py plan/apply/check --artifacts`; preserve their
accepted declarations. Use [concept models](concept-models.md) for model semantics.

1. Read the request, prior answers, adopted rules and owned-source evidence. Record
   original sources; distinguish user intent from agent interpretation.
2. Restore all relevant model roots. Add a `construction.targets` record when a
   requested model cannot yet form a valid draft: `target:` ID, kind, source refs,
   meaning, placement scope and unresolved details. It is not an executable node.
3. Record `construction.obligations` independently of questions: required models,
   state-owning objects and typed relationships. Compare these source-backed
   expectations with actual definitions. An empty question list proves no coverage.
4. Build valid candidate models. Preserve business loops, state cycles and shared
   rule dependencies. Containment does not satisfy a required flow or cross-model
   effect. Independent capabilities retain separate roots.
5. Resolve representation choices from existing answers and source facts. Ask only
   about remaining ambiguity that changes the meaning of this requested graph.
6. Show the affected model and its boundary. Preserve the exact presentation and
   confirmation sources, then bind and test the approved scope during coding.

Use `bo_concepts.py promote` with the current document digest and a valid candidate
to promote a target. It retains provenance and rejects stale/invalid replacements.
The inventory is derived from canonical models; do not maintain another forest file.

## Route work to its owner

Each new decision adds `routing` alongside its existing question, `affects`, sources,
status and history. The strict routing object contains:

| Field | Meaning |
|---|---|
| `kind` | `business_intent`, `technical_choice`, `implementation_fact`, `analysis_assumption`, `verification_gap` |
| `owner` | `human`, `agent`, or `checker` with a named `checker` |
| `stage` | `before_implementation`, `during_coding`, `before_acceptance`, `before_analysis` |
| `trigger`, `obligation_refs` | Actual ambiguity/evidence gap and the model work it resolves |
| `authority` | Source-backed `user`, `project_rule`, `delegated` or `engineering` scope |
| `evidence_required` | Conversation answer, source reference, runtime witness, independent assertion or checker receipt |
| `invalidated_by` | Meaning, source, environment, adapter, property or build changes |
| Optional `wording` | Equivalent business/technical wording under `en` and `zh-CN` |
| Optional `when` | Upstream decision and explicit option `choice`; also include it in `depends_on` |

Unknown intent belongs to the human unless explicitly delegated for that scope.
Source facts belong to the agent or checker. Engineering authority does not grant
permission to change business meaning. Intent cannot be postponed to optional analysis.

Offer one participation preference only if useful. `participation` stores source
refs, optional knowledge domains, `explanation_depth` (`outcome`, `technical`,
`mixed`), language and `preferred_participation` (`questions`, `review_groups`).
Skip it when already clear. Role and wording never confer decision authority.

One meaning can have two wordings: “Can a recipient start reading after access is
revoked?” and “Must the grant be rechecked at read-start?” Use this question only
when that timing is ambiguous in the request; it is not a default product policy.

## Small rounds, durable answers

```text
python SKILL/scripts/requirements_dialogue.py questions --file discovery.json --stage before_implementation
python SKILL/scripts/bo_concepts.py review --root PROJECT --stage before_implementation --review-model state-model:grant --locale zh-CN --url ACTUAL_GRAPH_URL --out review/current-model.json
```

Replace the example ID with an actual model. `review` returns a model index, one
Mermaid diagram using the shared graph projection, pending questions/targets,
omitted boundaries and separate intent/binding/runtime status. Show its Markdown
in chat with the verified viewer link. Review large models in focused groups.
Web remains a viewer; question cards or ordinary chat collect the answers.

The scheduler selects at most three ready human questions plus separate agent and
checker queues. Additional questions and conditional/deferred work remain recorded.
There is no total question limit. Existing unclassified questions stay available
while the agent supplies routing metadata.

Record prompts in `asked_in`. Partial replies add immutable `answers` fragments:
`id`, text, sources, affected refs, `kind: partial|contradiction`, optional `reply_to`.
Keep status `partial` or `contradicted` until an actual resolution. Silence leaves
the sent prompt pending. Follow up only on the unanswered part.

Preserve the complete old decision in `changes` when meaning/authority/routing
changes. Keep prior answer fragments and presentations. Changing/removing a
modeling obligation also uses `changes` with `obligation`, exact `previous`, sources
and reason. Unrelated pending scopes remain available after restart or role changes.

Implementation resolutions use `source_observation` or `checker_result`, with
typed evidence path, SHA-256 and covered refs. Record validation checks shape and
scope; it reports evidence verification as `not_checked`. Source/runtime checks
must still verify those claims. A user guess cannot certify an implementation fact.

## Show, then confirm

Generating a review does not record that a person saw or accepted it. After showing
it, use `bo_concepts.py present` with its exact snapshot, shown/explained refs,
omitted boundary and actual conversation source. Then `confirm --presentation ID
--scope ... --sources ...` preserves the confirmed meaning. A partial view cannot
approve omitted conditions. Changed meaning needs a fresh matching presentation.

Initial intent review uses `--stage before_implementation`. Source facts remain
coding work; optional analysis assumptions remain analysis work. Required gaps in
the active scope stay blocked while unrelated implementation can continue.
