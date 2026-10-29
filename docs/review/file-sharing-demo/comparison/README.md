# Assisted and unassisted file-sharing trials

Both conversations built the confirmed owner/recipient flow, added selected-recipient revocation, and repaired the same deliberately seeded wrong-identity deletion in isolated copies. Follow-up requirements and confirmations were scripted by the coordinating AI. Both used `gpt-6.1-sol` with `xhigh` reasoning. Original applications and independent expectations were retained.

## Observed result

| Aspect | Without VibeLens | With VibeLens |
|---|---|---|
| Initial application | 12 HTTP tests and 11 browser checks passed | 12 tests, 39 business assertions, 8 evidence checks and actual graph recording/replay passed |
| Revocation iteration | 20 HTTP and 22 browser checks passed | 16 tests, 84 business assertions, 10 evidence checks and real graph/browser replay passed |
| Organic permission defect in accepted V2 | None observed | None observed |
| Supplied diagnosis | Original 20 tests exposed 4 failures | Original 16 tests exposed 5 failures; native verify also failed |
| Actual localization | SQL source, independent SQLite rows and stale-page browser behavior | State remained shared, deletion affected zero rows and the grant remained; independent SQL binding and source confirmed the wrong variable |
| Repair | One SQL argument | One comparison operand; graph/source bindings refreshed through the normal gate |
| Retest | Original 20 HTTP, 22 browser and 19 added diagnostic checks passed | Original 16 tests, 84 business assertions, 10 evidence checks, original browser suites, other-recipient/regrant witnesses and real replay passed |
| Diagnosis turn elapsed | 507.605 seconds | 1,048.073 seconds |

Test counts overlap within each implementation and are not comparable coverage percentages. Turn elapsed includes evidence production, local environment and verification; it is not active human effort. Both workers found and repaired the defect. The assisted run produced a cross-layer explanation and maintained runtime map, while taking longer and generating more output for this case.

## Token use

The [complete table](cost-table.md) and [phase boundaries/counters](costs.json) separate gross input, cached input, uncached input and output. Reasoning output is already part of output and is not added again. Deltas use the final cumulative counter at named completed turns; negative/reset counters are rejected. Product-material export occurs after the diagnosis boundary and is excluded.

For initial development, uncached input was **217,341 with VibeLens / 156,298 without**; output was **150,496 / 46,864**. For controlled diagnosis, uncached input was **41,011 / 47,612**, output **48,019 / 18,836**. Gross input is much larger because repeated cached context is counted each time. These are token counters, not monetary charges.

The original assisted pilot included four framework upgrades and ten verification invocations during initial development. The later native-framework repair is shown as a separate phase. Framework stacks, observability/export requirements and conversation lengths also differ. This is a descriptive single-case comparison; it does not isolate the Skill's causal cost or establish a general diagnostic advantage. The additional fresh frozen-version trial checks usability without those in-flight source changes; it is not silently substituted for the original pair.

## Findings for the tool

- Shared predicates and bound expressions supported ownership, recipient access and reuse by view/download; the revoke iteration retained identities and refreshed source/runtime evidence.
- Canonical project validation and policy/database composition needed a real repair. Adapted trial success had concealed native integration gaps. Their original failures, canonical fixes and complete retests are retained in the shared-policy review.
- A recorded request field does not establish a driver's actual binding. The graph accurately exposed the failed effect; the precise binding needed independent driver/source evidence. Future capture improvements should preserve this distinction and redact actual bound values explicitly.
- Full graph/ownership JSON and repeated verification contribute substantial conversational cost. The Skill now asks the coding AI to keep complete payloads in files and inspect focused failures. Future measurement should use a fixed version, equivalent evidence tasks and multiple independently assigned builds.

See the paired [diagnosis records](../diagnosis/README.md) and the visible conversations under `../trials/`. The source setup scripts, screenshots, failed attempts and original expected values remain reviewable.
