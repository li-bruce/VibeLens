# Finite design analysis: source guide

The optional adapter consumes the existing canonical behavior contract and concept
registry. It owns no application scheduler, state machine or business baseline.

| Module | Responsibility |
|---|---|
| `value_types.py` | Shared scalar/collection fact carriers and native capture compatibility |
| `behavior/{domains,expressions,actions}.py` | Pure definition typing, frames and canonical transition updates |
| `analysis/capabilities.py` | Exact finite admission; unresolved or unsupported dimensions stay explicit |
| `analysis/tla/{values,expressions,exporter}.py` | Deterministic finite representation, one specification per property, original-ID map |
| `analysis/tla/toolchain.py` | Explicit optional download/cache, SHA-256 verification and Java 17 identity |
| `analysis/tla/process.py` | Fixed argument list, isolated environment, process cancellation and budgets |
| `analysis/tla/results.py` | Pinned TLC message protocol and typed value decoding |
| `analysis/runner.py` | Immutable attempt artifacts and scoped receipts |
| `analysis/artifacts.py` | Frozen-input comparison, byte hashes, re-export and raw-message verification |
| `analysis/trace.py` | Canonical logical steps and changes; no runtime events or durations |
| `workflow/analysis_cli.py`, `bo_analyze.py` | Thin configured-profile command boundary |
| `workflow/{sync_verify,behavior_iteration}.py` | Existing acceptance coordinator consumes verified optional evidence |
| `analysis-panel.js`, `logical-trace.js` | Read-only desktop graph selection and logical Timeline |

Definition validation does not load a JVM, import user code or download tools.
The runner never receives arbitrary shell commands. UI trace import is a display
operation and cannot create acceptance evidence. The graph's selected original
IDs are shared by 2D and 3D; logical steps do not enter runtime replay reducers.

## Representation and result boundaries

Generated variable names are independent of user text. Strings use an injective
UTF-8 hexadecimal carrier. Each parameter valuation produces a stable action
entry. `VLStep` and `VLCheck` retain action identity and transition constraints;
they are excluded from the physical tuple used by fairness. Auxiliary values can
increase TLC's state count: the two-owner oracle has four physical states and
the generated action-labelled representation has seventeen TLC states.

Declared domains constrain initial values and are checked as invariants. They
never filter `Next`; an out-of-range successor remains a counterexample.
Application-domain violations fail. Analysis-only bound overflow reports an
incomplete analysis. Explicit termination adds a self-loop only where its typed
condition is true; deadlock checks remain enabled elsewhere.

Every selected property is checked separately. A fairness assumption for one
property cannot strengthen another property's specification. Dependencies cover
all participating actions, including object-owned actions, variables and domains.
Original typed IDs, parameters, values and liveness closing edges survive export.

The supported and rejected subset is documented in
[the Skill reference](../../skills/vibelens/references/optional-analysis.md).
The adapter checks the selected design representation. Native correspondence,
external message guarantees, database atomicity and arbitrary activity engines
need their own evidence; they cannot inherit a design pass.

## Tool provenance

Pinned distribution: [TLC 1.7.4](https://github.com/tlaplus/tlaplus/releases/tag/v1.7.4),
SHA-256 `936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88`.
Tested runtime: Temurin Java 17.0.17+10; the adapter admits Java 17 and records the
exact version, executable and runtime release-file hashes. One worker is used.
The actual pinned release exposes the `-tool` message stream used here; newer
trace-export examples are not assumed to apply to it.

The [upstream message codes](https://github.com/tlaplus/tlaplus/blob/v1.7.4/tlatools/org.lamport.tlatools/src/tlc2/output/EC.java)
and [CLI implementation](https://github.com/tlaplus/tlaplus/blob/v1.7.4/tlatools/org.lamport.tlatools/src/tlc2/TLC.java)
are the parser and runner references. Preserve the upstream notices in the
downloaded distribution; source is under the
[upstream license](https://github.com/tlaplus/tlaplus/blob/v1.7.4/LICENSE).

Receipts detect drift and inconsistent artifacts, not forgery by an actor who
can rewrite the entire local evidence store. A full Java heap limit is not an
OS process RSS guarantee. These boundaries belong in technical review, not in
product-view labels.
