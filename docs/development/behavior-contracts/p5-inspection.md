# Behavior inspection

The initial business view stays compact. Behavior definitions appear in the
existing node details and use the same identities in 2D, 3D and recordings.
They describe what is declared; actual invocation values and durations retain
their existing runtime evidence and Timeline.

| Module | Ownership |
|---|---|
| `behavior/presentation.py` | Index variables, actions, properties and interactions against canonical concepts and declared native sites |
| `observation/behavior_context.py` | Pin details to the loaded project artifacts and read the last recorded verification |
| `behavior-details.js` | Render concise, expandable bilingual details in the existing panel |
| `analysis/trace.py` | Validate logical counterexamples and map steps to original graph identities |
| `logical-trace.js` | Prepare common graph selections and per-layer logical Timeline marks |

No additional graph nodes are created by the detail index. A shared definition
can appear at several mapped sites without acquiring several identities. Business
actions connect to state definitions through declared event/transition relations;
containment alone does not establish a behavioral link.

The detail panel's **Highlight dependencies** control selects the original mapped
identities through the shared renderer selection mechanism. It preserves the
camera and filters; hidden-layer paths retain their existing typed witnesses.

A recording retains its own definition context once, rather than copying the
complete contract into every frame. Live sessions detect changed pinned artifact
bytes, including same-size edits. A draft with a mismatched pinned definition stays
inspectable and reports unavailable details. The latest recorded verification
shows its candidate and date; it is not presented as approval of a newer live build.

Logical analysis traces use `bo-analysis-trace/v1`, `origin: model_analysis`,
`subject: design_model`, an exact definition hash, selected properties, complete
states and intervening action/parameter records. `loop_back` identifies an explicit
repeated state. Unknown identities and malformed steps are rejected. Values outside
the declared domain remain visible as findings. The projection retains original
node/edge IDs, value changes and logical indices. It adds no timestamps, call
instances or physical execution edges. Actual TLC import and interactive analysis
selection are P6; this phase provides their shared adapter.

Evidence and scope: [P5 review](../../review/behavior-contracts-sequential/p5-viewer/README.md).
