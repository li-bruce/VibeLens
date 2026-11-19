# Guided construction and scoped review

This reference describes the P2 implementation. The phase verdict and executed
checks are recorded in [progress.json](progress.json) and its evidence links.
It does not attest to the independent conversations reserved for P7.

## One model and decision store

`business-discovery/v3` remains the authority for conceptual definitions, request
sources, construction obligations, decisions, presentations and confirmations.
The model index and review workbook are generated from those records. A missing
model remains a construction target until promotion passes the existing model
validators. A model with no outstanding questions may still have unresolved
construction obligations.

Decisions can add `routing`: kind, owner, stage, authority, obligation references,
evidence requirements and invalidation conditions. Human intent questions stay
separate from source facts and verification work. Engineering authority does not
authorize a change to business meaning. A named checker needs a checker receipt;
its name alone is not execution evidence.

Participation preferences select authored business or technical wording and the
display language. They do not change authority, graph IDs or semantic snapshots.
An explicit review locale applies to the diagram and questions without editing
the saved preference. If localized wording is absent, the original question is
retained for the coding agent to explain in the conversation.

## Scheduling and recovery

The existing dialogue assessment accepts a selected scope and stage. It retains
all decisions, while scheduling at most three ready human questions and separate
agent/checker queues. Dependencies and conditional choices determine readiness.
An unanswered prompt waits; a partial reply permits a focused follow-up. Free text
does not silently become a structured option. Conditional inactive decisions and
future-stage work remain in the report and history.

Source-backed target placement scopes unfinished work. A cycle is invalid; an
unplaced target remains a visible gap. An unrelated future capability does not
block a confirmed current increment. Changing or deleting an obligation requires
its previous record and an explicit user/project-rule basis.

Old discovery versions keep their original clarification behavior. Unvalidated
V3 routing metadata cannot make a V2 blocking question disappear. An unclassified
V3 question remains available while classification is assigned to the agent.

## Review and confirmation

```text
bo_concepts.py review --root PROJECT --scope MODEL_REF
    --review-model MODEL_REF --stage before_implementation
    --locale zh-CN --url http://127.0.0.1:PORT/graph --out review.json
```

Use the actual viewer address and a canonical model reference, such as
`business-network:sharing`. The command emits a compact model index, one focused
Mermaid graph and pending questions. The stored workbook retains the shared
focus projection, exact semantic revision, shown assertions and omitted scope.
Definition validity, intent confirmation, source binding, engine support and
runtime verification are reported separately.

Generating a review is not evidence that a person saw it. The agent presents it
in the conversation, records the actual presentation through the existing
`present` command, and uses the user's reply for `confirm`. A changed semantic
snapshot or an omitted boundary cannot be confirmed by a stale partial preview.
The Web application remains a viewer.

## Source ownership

| Module | Responsibility |
|---|---|
| `concepts/construction.py` | Obligation validity, target placement and scoped gaps |
| `concepts/decision_contract.py` | V3 routing, authority, provenance and immutable history |
| `workflow/requirements_dialogue.py` | Existing dialogue validation and stage/scope integration |
| `workflow/question_routing.py` | Ready queues and wording projection, with no file IO |
| `workflow/construction_review.py` | Derived model inventory, focus projection and Markdown |
| `workflow/concept_cli.py` | Existing lock, path, command and artifact boundary |

`tests/test_guided_construction.py` exercises these services with synthetic
records and an actual CLI invocation. Source evidence references remain
`not_checked` until later source/runtime verification consumes their artifacts.
