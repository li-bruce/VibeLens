# v0.11.3 independent audit: retained results

[Audit 01](observer-v0113-independent-01.md) is retained unchanged. Its initial
optional sidecar check compared a deliberately redacted query placeholder with
the actual local session namespace and conflated that unavailable comparison
with observer exclusion. That comparison was not evidence of a child-project
scope mismatch.

[Audit 02](observer-v0113-independent-02.md) keeps the business recording and
UI-only capture separate. It checks their actual saved files, hashes, accepted
builds and IDs. UI-only 0 → 0 → 0, no gaps, completed producer flush, zero pending,
revision 108 → 109 save ACK, current private namespace-file consistency, and the
unchanged default revision 174 pass. Raw URL identity remains `None` because the
source receipt normalized that field before it was retained. No placeholder is
accepted as the original query value.

The local session is a deterministic UI namespace, not classified here as an
authentication credential. Redaction is for privacy. Native mapping, state rules,
project checks and business assertions are still reported separately. Neither
audit overrides the [first default preservation failure](remark-v2/upgrade-v0113-01/default-preservation-proof.json).
The complete turn remains **not all-passed**, with the earlier writer unresolved.

The independent auditor imports no application modules, sends no requests and
runs no business/native commands. It reads existing declarations, receipts and
hashes only. Private snapshots and raw record payloads remain local.
