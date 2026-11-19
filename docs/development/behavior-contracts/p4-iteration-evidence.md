# P4: iteration closure and scoped evidence

The existing change coordinator owns recall, snapshots, verification and acceptance.
Behavior services add typed impact, per-record change review and separate coverage.
They never execute the application or accept a batch independently.

| Module | Responsibility |
|---|---|
| `behavior/dependencies.py` | Derive prerequisites from canonical concepts, expressions, interactions and source/check inputs; walk both old and new graphs |
| `behavior/iteration.py` | Distinguish meaning from implementation and analysis-only limits; require a recorded request basis per changed definition |
| `behavior/evidence.py` | Retain an executed outcome, artifact hashes and exact dependencies; explain freshness separately from correctness |
| `behavior/coverage.py` | Derive denominators from configured definitions and cases; expose missing evidence independently in each category |
| `workflow/behavior_iteration.py` | Attach these results to the original receipt without replacing any gate |

`inspect` restores durable recall and writes full `behavior-impact.json`. Prompt
impact lists are bounded, with total and omitted counts. Shared-rule and interaction
consumers are included even when hidden in the viewer. New source still enters via
the existing independent inventory; a smaller authored graph cannot exclude it.

Design evidence follows semantic dependencies. Native evidence additionally follows
owned source, source structure, adapters and protected checks. Current comparison is
deliberately conservative: an adapter change invalidates native evidence broadly.
The original exact-candidate acceptance remains necessary after any source edit.
Fingerprints detect stale or incomplete records; they are not signatures against a
malicious author rewriting the whole repository.

Every coverage category exposes its expected identities, checked identities, gaps
and executed errors. Correctly captured invalid values remain valid observations
and separate native-domain findings. Analysis-only bounds do not constrain runtime
values. Required analysis with missing, stale, conflicting or unsupported evidence
blocks acceptance. Actual analysis execution and verified artifact import are P6.

The host integration is explicit workflow invocation in the activated conversation.
Missing recall is restored on inspection; files cannot force a model to read them.
Source freshness, binding, capture and acceptance checks remain the enforcement
boundary. No automatic global hook is claimed.

Regression and failure records: [P4 evidence](../../review/behavior-contracts-sequential/p4-closure/README.md).
