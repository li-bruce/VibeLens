# Optional finite design analysis

Use this after the business, state and rule networks and their behavior contract
are valid. The application keeps its native state executor. The observer runs the
model checker out of process; it does not change business values or limits.

## Select the question and its scope

Choose a configured `bo-analysis-profile/v1` ID from the pinned project bundle.
Retain all declared model owners, actions and dependencies. A hidden graph layer
does not narrow the checked design. Record application limits separately from
analysis bounds, and obtain the normal scoped confirmation for a changed business
meaning or scheduling assumption. Technical choices stay with the coding agent.

The first adapter checks a **design_model**: flat state transitions, Boolean or
homogeneous enum values, bounded integers, fixed identity pools, finite sets and
bounded sequences. Explicit `append`/`tail` model a finite FIFO; explicit set
updates model a finite holder set. These are declared observable values, not
hidden exporter state. Shared Boolean policy expressions retain canonical IDs.

Supported properties are state invariants, transition postconditions and a
trigger that must eventually reach a condition. Weak/strong fairness applies
only to the explicit action set of a confirmed scheduling assumption, separately
for each property. The checker never adds fairness or filters out failing states.

Unsupported: arbitrary callbacks, hierarchical/parallel engine semantics,
activity resource/join translation, transactional consistency, delivery/retry/
deduplication protocols, maps, recovery initialization, native refinements and
implementation equivalence. A bounded queue alone does not establish message
delivery; a holder set alone does not verify the native activity scheduler.
Admission reports these boundaries instead of omitting their behavior. Ordinary
source/native-runtime checks still apply to all of them.

## Run and inspect

Install a Java 17 runtime. The optional TLC 1.7.4 JAR is downloaded only when asked:

```text
python SKILL/scripts/bo_analyze.py install-tool
python SKILL/scripts/bo_analyze.py run --root PROJECT --profile PROFILE_ID
python SKILL/scripts/bo_analyze.py check --root PROJECT
```

`VIBELENS_JAVA` selects the Java executable; `VIBELENS_TLC_JAR` selects an existing
checksum-matched JAR. Default cache: `~/.cache/vibelens/tools/tlc-1.7.4/`.
Neither Java nor TLC goes into the application or Skill install package.

Each invocation creates an immutable `.stategraph/analysis/<attempt>/` containing
the frozen inputs, generated TLA/configuration, stable-ID source map, raw tool
output, exit/cancellation information and receipt. The profile's wall budget is
shared across properties. Heap, output and temporary state storage are bounded;
the JVM's total RSS includes additional native memory. Ctrl+C cancels exploration
and retains an incomplete result. No application secrets are inherited.

A pass is a completed nonempty exploration of the selected finite design. A
violated property, deadlock, empty initial set, parser/tool error, missing tool,
timeout or out-of-analysis-domain value has a separate result. Expected terminal
states need a typed `termination.condition` with recorded `source_refs`; there
is no automatic "no outgoing transition means finished" rule.

Open a failed run's `property-N/logical-trace.json` through **Model trace** in the
viewer. Drag the logical-step cursor to inspect exact changes, original nodes and
definition links in 2D/3D. Loop witnesses stay visible. This is model evidence;
record an actual application reproduction separately with real invocation times.
If the model trace and native reproduction differ, retain and investigate both.

## Close the coding batch

`change_sync verify` rechecks saved artifacts, regenerates the exact model and
reparses raw TLC messages before using a formal receipt. Changed definitions,
properties, bounds, assumptions or adapter code invalidate it. A source-only
refactor does not automatically invalidate unchanged design evidence; native
mapping and runtime checks must still run. A cancelled attempt remains archived
when a later complete proof covers the same dependencies and tool. Conflicting
completed results block acceptance.

Missing optional tools never stop application execution. Required analysis
profiles with missing/stale/incomplete evidence do block iteration acceptance.
Do not accept a batch from a model pass alone or alter protected expectations to
make it pass. The original mapping, capture, native state, business and project
checks retain their own results and authority.
