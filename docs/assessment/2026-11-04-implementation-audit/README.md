# Follow-up audit: layer consolidation and concept-first development

Date: 2026-11-04. Audited branch: `feat/concept-model-contracts`.
Audited commit: `ce0a1fa6f16d85e83e9ce5b95dfd6750aec16c6f`.

This audit checks the two proposals quoted by the user against maintained source,
targeted regressions and new counterexamples. Product source and accepted example
baselines were not changed. The previous acceptance remains evidence for its
executed cases; it does not cover the counterexamples discovered here.

Inputs: [layer assessment](../2026-11-04-layers/README.md),
[concept-first proposal](../../development/concept-model-first.md), and
[implementation acceptance](../../review/concept-models-20261104/README.md).

## Conclusion

The main architecture and workflow have been implemented. This is no longer a
design-only proposal. However, the two proposals are **partially fulfilled**, not
fully closed: two confirmed-to-native association checks are missing, and three
viewer cases lose meaningful relationships or condition polarity.

The highest priority is to check the relationships between implemented models,
not merely the validity of each model in isolation. After that, repair the
projection and preset gaps and promote the counterexamples to regression tests.

## 1. Layer proposal coverage

| Requirement | Status | Current implementation and remaining boundary |
| --- | --- | --- |
| Business remains the user-oriented entry | Implemented | Business actions remain distinct from HTTP registrations and function declarations. Overview combines business, state and rules; each has a focused preset. |
| State model remains independent even when displayed with business | Partial | Native and conceptual state definitions remain independent. The 2D conceptual containment defect F4 prevents a complete hierarchy display. |
| Rules, capacity and joins have different meanings | Implemented | Shared policy definitions map to rules; resource/wait/join execution concerns map to state. They retain their native types. |
| API is an implementation entry facet | Implemented for current HTTP support | Receiver-specific registration identity remains separate from handler identity. This does not establish complete CLI, message-consumer or GUI-callback extraction. |
| Core/observed functions share physical declarations | Implemented | One physical source identity is referenced by semantic and contextual nodes. Different observation actions and runtime calls retain their own IDs. Path or qualified-symbol changes still need rebinding; labels do not establish equivalence. |
| Project structure and symbols form coarse/fine implementation navigation | Implemented | Directory/file/definition/parameter relations and separate project/code presets remain. File containment alone does not prove architectural quality. |
| Functions and parameters remain connected after consolidation | Partial | Nodes are included, but the Functions preset excludes their static relation types (F5). |
| Data access becomes an implementation facet | Implemented | Read, write, transaction and transformation roles remain distinct; data-access views combine operations and storage targets. Complete row/column lineage is not claimed. |
| Captured fields do not dominate default views | Implemented | Full field inventory remains available; ordinary capture detail is filtered by default and can be promoted or explicitly shown. A recorded JSON field does not become a lexical variable. |
| Storage structure remains independently available | Implemented, wording differs | Stores, datasets and columns retain structural identity. Labels still use Data structure/Database structure rather than the narrower suggested Storage structure. |
| Separate containment, source mapping, execution parenting and display grouping | Partial | Typed source/concept relations and runtime parent IDs are separated, but the renderer still consumes a single display `parent` tree. F4 demonstrates an incomplete adapter. |
| Hidden layers retain explained paths | Implemented with bounds | Shared projection retains ordered original witnesses, marks structural indirect edges and cuts traversal at explicit exclusions. Limits are depth 12, work 25,000, edges 800, witnesses 4; completeness is reported. |
| Lifecycles refer to real execution, not static containment | Implemented | Actual call intervals and observed state residencies feed Graph/Timeline. Each bound invocation is preserved; static folders and unobserved functions do not acquire invented execution periods. |

Source entry points: [classification](../../../skills/vibelens/assets/stategraph-viewer/graph-classification.js),
[views](../../../skills/vibelens/assets/stategraph-viewer/analysis.js),
[layer selection](../../../skills/vibelens/assets/stategraph-viewer/graph-layers.js),
[source identity](../../../skills/vibelens/scripts/bo_observer/graph/source_identity.py),
[hidden paths](../../../skills/vibelens/assets/stategraph-viewer/hidden-paths.js),
[concept observation](../../../skills/vibelens/assets/stategraph-viewer/concept-observation.js).

Five regular concerns plus an unclassified diagnostic concern are defined in the
current classifier. Users select and combine views/facets; projects do not have
to display every concern. Arbitrary user-defined plane semantics are not an
implemented capability.

## 2. Concept-first proposal coverage

| Requirement | Status | Current implementation and remaining boundary |
| --- | --- | --- |
| Build three peer models before source exists | Implemented | `business-discovery/v2` assembles business networks, object state models and shared Boolean policy definitions; previews need no fake implementation or runtime evidence. |
| State owner, identity, typed events/context, initial state and ordered transitions | Implemented in the definition contract | State references, payloads, guards, effects and declared execution constraints are validated. The generic binding compares identity declarations; project-specific runtime evidence must still establish the actual object key. |
| Shared rule inputs, composition, parameter bindings and read basis | Implemented in the definition contract | Logical changes, arguments and fact read timing participate in confirmation and binding. Decision outputs remain Boolean; full DMN or recursive relation evaluation is not implied. |
| Scope-based confirmation with original answer evidence | Implemented | Immutable semantic snapshots, recorded source evidence, dependency closure and impact on previously confirmed consumers are checked. The host supplies truthful conversation evidence. |
| AND-to-OR, guard, transition/order and read-basis drift | Implemented | Native semantic comparison and history gates reject tested mutations. The AND-to-OR control also failed as expected during this audit. |
| Business operation constrained by its confirmed rule | Incomplete | F1: moving a policy operation to a different native business target can pass the concept binding check. |
| Transition effects and completion boundary bind to implementation | Incomplete | F2: a declared effect can bind to an unrelated source-backed operation without a mandatory transition-effect witness or completion assertion. |
| Source bindings and independent expected outcomes | Implemented framework | Binding requires source anchors and exact independent expected assertions; existing source, runtime and business runners remain necessary. Declaration legality alone cannot establish execution. |
| Multiple independent state models | Unsupported by the new binding | Multiple active conceptual models are rejected explicitly. One primary native machine is supported; this does not cover all file/grant/job state-model combinations. |
| Hierarchy, parallelism, waiting, resources and joins | Bounded support | Definitions can describe hierarchy. Native adapters determine supported HSM semantics; `bo.fsm/1` is flat. Activity support is run-scoped with declared activities, integer capacity and ALL join, not a general distributed Petri engine. |
| Drive and observe preserve native authority | Implemented | Project-native code/engine controls transitions, rules and effects; the external observer records and presents them. |
| Every iteration restores and checks obligations | Implemented agent workflow | Recall, begin, scan, inspect, verify, accept and check are connected; v2 cannot silently downgrade. The host/coding agent must invoke the workflow. |
| Separate result categories | Implemented, small metadata omission | Verification emits concepts, mapping, state_rules, business and project_checks. Recall's required report list still omits concepts (W1). |
| Realistic dialogue and full runtime verification | Partial evidence coverage | Retained trial is an independent AI developer with simulated user replies, running a real Python observe-mode app through an iteration. It is not a human study or a native Node/new-v2-drive full-cycle trial. |

The old empty `graph.machine` observation needs a specific correction:
[registry.py](../../../skills/vibelens/scripts/bo_observer/concepts/registry.py#L148)
still uses an empty runtime-machine envelope for design display. Complete state
definitions now live in `discovery.state_models`, with events, guards, effects
and transitions projected independently. This is deliberate separation of draft
semantics from an executable native declaration, not the original missing draft.

## 3. Reproduced findings

### F1 — High: rule-to-business applicability is not checked against native targets

Confirmed behavior: the `read` business operation requires the `read` policy.
The probe changes that policy operation's `business_nodes` from `native:read` to
`native:share` and regenerates its otherwise legal policy projection. The concept
assessment still returns `valid: true, ready: true`.

`concepts/rules.py:12` correctly removes native `business_nodes` from portable
policy meaning. However, `concepts/obligations.py:112` generates an applicability
relationship without a matching native-target check. `concepts/anchors.py:117`
only checks explicit crosslinks. A correct policy graph can therefore be attached
to the wrong implemented business operation at this gate.

Repair: resolve each applicable business operation through `binding.business`,
compare those native targets with the corresponding policy operation, and check
that runtime evaluations belong to the relevant business invocation. Add a
negative test that moves a rule target while preserving every policy ID.

### F2 — High: transition effects do not create mandatory native association and completion checks

The probe declares `store_grant` as an effect of `grant-share`, with completion
defined as transaction commit, then binds the effect to unrelated `native:read`.
No explicit `transition_has_effect` crosslink is supplied. The concept assessment
still returns `valid: true, ready: true`.

`concepts/binding.py:22` compares native transitions without their effects;
`concepts/assertions.py:10` requires a source-backed operation for an effect but
does not establish its association with the transition. `state.py:115` retains
completion as confirmed text. An optional extra crosslink can add a structural
check, but the transition's own effect declaration does not require it.

Repair: derive required bindings from every transition effect, including its
native invocation/event and completion evidence. For a transaction effect, bind
the actual transaction identity and commit boundary or a suitable independent
outcome assertion. Add wrong-function, missing-event and wrong-transaction cases.

**F1/F2 evidence boundary:** the reproductions run concept assessment, exact policy
projection checks, native state-definition validation and a clearly synthetic
signature inventory. They do not run mutated full-project acceptance. The result
proves missing association checks in these gates, not that every downstream
business test would accept an incorrect application.

Evidence: [script](evidence/concept-negative-cases.py),
[result](evidence/concept-negative-cases.json). The unchanged baseline passes;
the AND-to-OR control correctly fails with `rule_semantics_changed_during_binding`.

### F3 — Medium: positive and negative guards have identical displayed edges

Change `conditions: [may_manage]` to `unless: [may_manage]` on the first declared
transition. `state_projection.py:143` computes `negated`, but
`registry.py:94` drops that relation value while emitting graph edges. Both
versions show the same `guarded_by` edge labelled Requires.

The canonical semantic record and the transition's on-demand JSON definition
remain correct. This is a graph-expression defect, not corruption of confirmed
semantics. A user confirming the diagram cannot distinguish the two conditions
from that edge. Preserve polarity in projected relation data and readable labels;
also retain transition event/guard metadata rather than dropping it generically.

Evidence: [script](evidence/guard-polarity-repro.py),
[positive/negative graph and semantic records](evidence/guard-polarity-repro.json).

### F4 — Medium: conceptual state containment disappears in ordinary 2D

`state_projection.py:58` emits state membership as `contains` edges without the
display `parent` field. `layout.js:274` builds regions only from `parent`, while
`layout.js:637` suppresses containment edges in unlayered 2D on the assumption
that regions already express them.

The probe produces three state nodes and two raw containment relations, but zero
regions and zero drawn edges. The same input with layered rendering produces the
two edges. This confirms a 2D/layered presentation mismatch using the actual
viewer projection functions, without claiming a new visual browser test.

Repair: adapt semantic state containment into the appropriate display hierarchy,
and only suppress an edge if a visible region actually represents it. Keep file,
state, business and runtime-parent semantics independently typed.

### F5 — Medium: Functions and parameters filters out static function relationships

`analysis.js:105` includes `code-function`, `code-parameter` and `code-reference`
nodes but its allowed relation list omits `code-calls`, `code-parameter` and
`code-maps`. With two physical functions and a parameter, all three glyphs are
shown and both original relationships are filtered out. The Code structure
preset displays both relationships on the same input.

Repair the preset's relation family and test every preset with endpoints and
relationships together. Keeping all three node types is insufficient evidence
that the view is complete.

F4/F5 evidence: [script](evidence/layer-view-repro.mjs),
[2D/layered and Functions/Code comparisons](evidence/layer-view-repro.json).

## 4. Workflow and evidence gaps

- **W1: recall metadata.** `workflow/iteration_recall.py:129` lists four reports,
  omitting `concepts`. The verification gate actually emits and checks five; this
  is a prompt/metadata inconsistency, not a demonstrated bypass.
- **W2: browser regression automation.** The new accepted-v2
  `tools/test_concept_browser.mjs` was run and retained previously, but is absent
  from `tools/verify.py` and `.github/workflows/check.yml`. Add a self-contained
  accepted fixture/server setup and include it in the browser job.
- **W3: confirmation presentation.** The Chinese trial's generated diagrams use
  English labels and protocol relation names. The first business preview has
  eight internal nodes and fifteen boundary stubs, including repeated external
  objects. This falls short of the concise user-language preview in the Skill.
  Deduplicate boundaries, localize presentation labels and recheck the delivered
  conversation; preserve the original trial evidence.
- **Maintenance trigger boundary.** `workflow/bo_sync.py:361,398` reports
  `ai_invocation: host_or_coding_agent_required`. Durable recall and source scans
  exist; they do not independently force a host LLM to execute every turn or repair
  code. Describe the capability as an enforced acceptance workflow when invoked.

## 5. Checks performed in this audit

Using the repository virtual environment, these targeted tests passed:

| Entry point | Result |
| --- | --- |
| `tests/test_concept_models.py` | 36 passed |
| `tests/test_concept_workflow.py` | 21 passed |
| `tests/test_concept_capture.py` | 10 passed |
| `tests/test_layer_source_identity.py` | 14 passed |
| `tools/test_concern_projection.mjs` | Passed |
| `tools/test_concept_view.mjs` | Passed |
| `tools/test_concept_observation.mjs` | Passed |
| `tools/test_trace_lifecycles.mjs` | Passed |
| `tools/test_view_continuity.mjs` | Passed |

The four Python suites total 81 tests. Five Node entry points passed; their
internal assertions are not combined into a fabricated test count.
[Command receipts](evidence/results.json) and individual logs are retained.
The three additional reproduction scripts demonstrate five outstanding defects;
their exit code zero means the stated defect was reproduced, not repaired.

This audit did not rerun the full repository, live databases or browser suite.
Those results remain dated evidence in the preceding acceptance report. No new
release, branch merge, deployment or human usability study is claimed here.

From the repository root, reproduce the new findings with:

```text
.venv/Scripts/python.exe -B docs/assessment/2026-11-04-implementation-audit/evidence/concept-negative-cases.py
.venv/Scripts/python.exe -B docs/assessment/2026-11-04-implementation-audit/evidence/guard-polarity-repro.py
node docs/assessment/2026-11-04-implementation-audit/evidence/layer-view-repro.mjs
```

## 6. Closure order

1. Repair F1/F2 and require native association/completion witnesses, keeping all
   existing policy, source, runtime and independent business checks.
2. Repair F3/F4/F5; add semantic-edge and preset-completeness regressions shared
   by 2D, layered/3D and focused views.
3. Fix W1, wire W2 and improve W3, then rerun the full acceptance and actual
   browser interactions. Extend new-v2 end-to-end coverage to drive mode and a
   native Node project before claiming those combinations are fully exercised.
4. Treat multiple state models and universally checked composite runtime object
   identity as explicit additional work, rather than silently describing them as
   covered by the one-machine fixture.
