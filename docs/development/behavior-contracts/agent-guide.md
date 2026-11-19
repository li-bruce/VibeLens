# AI development guide: behavior contracts

This is the engineering handoff for the next implementation task. It is not an
installed Skill activation rule and does not activate VibeLens or ARIS in another
chat. Follow the user's active authorization and the repository's applicable
instructions.

## Read before changing code

1. [Overview and requirements](README.md).
2. [Current implementation audit](audit.md).
3. [Protocol and semantics](protocol.md).
4. [Ordered implementation plan](implementation.md).
5. [Acceptance cases](acceptance.md).
6. Existing [Skill](../../../skills/vibelens/SKILL.md),
   [source guide](../../source-guide.en.md) and focused references for your change.
7. [Model construction through dialogue](model-construction.md), including its
   source audit and P0–P7 corrections. Apply this to the whole plan, not only the
   question wording or first-use preference prompt.

Check the actual branch and working tree. The complete plan is committed at
`a8f569d7`, with production code from `106fddb3`. Implementation restarted on
`feat/behavior-contracts-sequential`. Read [progress.json](progress.json) and each
phase's evidence: P0 is complete; P1's definition slices are implemented, while
the remainder of P1 and P2–P7 remain open. Preserve the recovery stash and unrelated
work. Do not use the abandoned draft or premature trial chats as acceptance.

## Protected product behavior

- Preserve project-native execution, independent state modules and the external
  observer. Drive/observe stay distinct. The optional checker never authorizes or
  performs business effects.
- Preserve independent business/state/rule networks, all registered state models,
  stable IDs, source ownership, layout, personal notes and existing strict checks.
- Clarify current user intent without inventing extra business policy. Human
  authority, technical knowledge and participation preference are separate.
- Questions about source facts belong to the coding process. Back answers with
  current source and executed cases. Silence and AI prose are not user approval.
- The guided dialogue constructs and confirms the applicable model collections,
  their internal relationships and boundaries. Restore a model inventory, identify
  modeling gaps, review the affected network and bind its obligations. A list of
  answered requirements questions is insufficient evidence of model construction.
- Preserve loops, shared rules and independent capabilities. The user's "forest"
  does not impose tree topology or require one state model per application/layer.
- Observe invalid behavior faithfully. Never replace actual values with modeled
  values to obtain a pass. Mapping and business correctness remain separate.
- Treat analysis bounds, production limits and abstractions as different inputs.
  A finite model pass is limited to its exact properties, assumptions and version.
- Do not modify framework code inside an application trial. Repair the maintained
  framework, rebuild managed adapters and retest a fresh installation.
- Keep application integration small. Tool dependencies, viewer and TLC stay
  outside production application bundles. Preserve explicit chat activation and
  `/vibelens` control allowlists.

## Start with P0, then P1

1. Record the current implementation/test baseline and outstanding failures.
2. Resolve protocol versioning and canonical ownership before creating consumers.
3. Add valid, invalid and legacy fixtures before or alongside the first validator.
4. Implement one coherent phase/slice; update its requirement-to-case mapping.
5. Integrate it through existing commands and services. Do not build a parallel
   project coordinator, state engine, policy engine or graph registry.
6. Continue in the dependency order recorded in `implementation.md`.

The user authorized this planning delivery first. Subsequent implementation scope
comes from the active task. Do not treat this file as authorization to publish,
create chats, delete unrelated files or change confirmed application requirements.

## Required coding-batch behavior

For framework development, restore this plan and current implementation status.
For each adopted application/trial batch, use the existing recall/begin/scan/
inspect/verify/accept/check workflow. Extend it with the new obligations as those
phases become available; do not claim not-yet-implemented hooks already ran.

Before editing, identify:

- affected requirement/model/action/property IDs and cross-model dependents;
- additions, retirements, splits/merges and unresolved construction targets in the
  model inventory, with their source basis and review status;
- whether meaning changes or only source/bindings change;
- source files, probe/reader owners and supported native capabilities;
- existing evidence that will become stale;
- tests that should fail if this change is implemented incorrectly.

After editing:

1. Scan owned source independently of the existing graph.
2. Reconcile definitions, source docs, parameters, probes and native boundaries.
3. Route actual ambiguity to the correct owner; continue unrelated work.
4. Run relevant existing and new checks with independent expectations.
5. Exercise a relevant negative case without weakening the accepted baseline.
6. Preserve failure, repair and retest evidence and exact candidate fingerprints.
7. Update phase status, source guide and the handoff's next concrete action.

Mandatory check omissions block acceptance for their affected scope. Optional
formal analysis may be unavailable while ordinary observation works; report that
distinction explicitly. No background file watcher is assumed to wake an arbitrary
host or perform semantic reconciliation without an active integration.

## Engineering conventions

- English identifiers, source comments and canonical docs; UI and dialogue use
  their selected language. Display translations do not change canonical IDs.
- Use the module ownership table. Pure semantics, filesystem IO, subprocesses,
  host integration and rendering have separate responsibilities.
- Add helpful docstrings on main functions: input/output, side effects, failure
  behavior and evidence meaning. Avoid narration that repeats the code.
- Use existing shared graph/Timeline presentation; never implement the same
  contract behavior separately for each layer or 2D/3D renderer.
- Reject invalid definitions and unsupported semantics explicitly. Preserve
  runtime evidence gaps and mismatches, including old-build observations.
- Do not scan dependency/build/runtime directories or harvest credentials and
  arbitrary request bodies. Use the established source and capture scopes.
- Read current CLI schemas/help before invoking commands. Proposed APIs in this
  plan are not executable until their phase is implemented.

## What each delivery must report

| Item | Required content |
|---|---|
| Scope | Phase and BC/A IDs completed, changed modules and unsupported items |
| Behavior | What now works and why it matches the confirmed intent |
| Evidence | Exact commands/exits, source/build/version, failures and final rerun |
| Separation | Mapping, capture, business, state, project and analysis outcomes |
| Compatibility | Legacy fixtures, native execution, personal views and package checks |
| Next action | First unfinished dependency and the evidence needed to close it |

Do not mark a phase complete because documentation or a screenshot exists.
Publish product copy only for accepted functionality. Independent dialogue trials
must distinguish simulated user answers, actual runtime records and model traces.
