# P7 — Independent candidate trials

The later canonical repairs and their separate gates are indexed in
[`repair-09`](repair-09/README.md), [`repair-10`](repair-10/README.md) and
[`repair-11`](repair-11/README.md), [`repair-12`](repair-12/README.md) and
[`repair-13`](repair-13/README.md).
The original failed recordings remain preserved. Current native acceptance,
iteration and complete desktop checks are still open; a repair gate alone does
not close this phase.

Status: in progress. P0–P6 were implemented, regressed and committed before
creating either trial. Initial candidate: `87ab32d5` on
`feat/behavior-contracts-sequential`. No merge, release or public deployment.

The first design attempts exposed shared viewer/preview issues before any native
application implementation. See [initial review and repair](design-review.md).
Those attempts and screenshots remain separate from the subsequent clean-install
retest. The full P7 acceptance remains open.

Two fresh isolated installations were created with `tools/install_skill.py`.
The coding chats receive only their candidate Skill, target directory and a
natural application request. The evaluator's intended choices are not sent to
them. Follow-ups answer actual questions; they are simulated user decisions,
not statements of the repository owner's production policy.
These are fresh chats on the same workstation, not memory-isolated experiments:
the host supplies its normal project memory. Only explicitly answered trial
requirements may become application policy.

## Evaluator expectations

Both apps: a small local file-sharing tool and a separate announcements board.
Uploads belong to their uploader; shares identify individual recipients; only
owners manage file grants. Announcement editors manage the independent board.
Seeded synthetic accounts and local SQLite are sufficient. Keep identities of
file grants, download jobs and announcements independent; reuse applicable
authentication/ownership predicates rather than duplicating rule meanings.

Python: choose drive mode when asked. A queued download checks current permission
when work starts; revocation blocks work that has not started, while an already
started transfer may finish. Node: choose observe mode, preserving native logic.
For a distinct valid policy, a download accepted into the queue may finish after
revocation; new requests must fail. Do not disclose these timing choices before
the coding chat asks or shows its interpretation for review.

The first Python answer clarified that the relevant boundary is the worker
starting file preparation; a task already preparing may finish and its owner may
retrieve that result. This clarification precedes implementation and must remain
visible in the model/review history.

Correct a material interpretation in the draft when needed, confirm its actual
scope, implement and independently inspect runtime and every configured layer.
Then request one business change and one source-only refactor, checking graph
changes, retained unrelated models/views, scan/verification and original captures.
Source facts stay with the coding process; unanswered questions and host approvals
are not fabricated user confirmations.

Framework failures are repaired in the maintained Skill first and tested again
in a fresh trial. Retain dialogue, original failures, repair revisions, final
source/model bundles, test outputs and desktop screenshots. Product content is
updated only after the applicable trial evidence is accepted.

The first canonical repair passed its full regression, selected TLC checks and
clean-export gates: [repair receipt](repair-01/results.json). P7 remains open;
clean-install retests use Python drive and Node observe, as explicitly confirmed
by the repository owner. Initial attempts were stopped before native coding.

## Native trial findings and next gate

The fresh retests use candidate `e9d8ee50`. Python drive is chat
`01a1f415-d28c-72b1-ae26-0c89f9b4aed0`; Node observe is chat
`01a1f415-e2a9-7171-86f8-ec87707ead07`. Public dialogue snapshots and simulated
answers are in `dialogue/`. The first native source archives are explicitly
in-progress snapshots, not accepted application releases.

The shared Flask boundary repair was committed as `9d03525e` with its
[full regression and export receipt](repair-02/results.json). Independent native
requests also exposed a missing origin-rejection return in the Node trial;
[repair 03](repair-03/README.md) records the actual failure and reusable Node
adapter checks. Observer health being clear does not prove every response was
captured: actual response outcomes must be compared with recorded boundaries.

The Node retest then refused the known two-to-three-file dependency upgrade.
[Repair 04](repair-04/README.md) preserves that failure and adds an explicit
receipt-preserving migration. The trial's business definitions stay unchanged.

[Repair 05](repair-05/README.md) removes managed upgrade backups and registered
definition files from the application engineering view. Independent source
coverage and watched-file integrity checks retain their original scope.

Before closing P7, both retests must use the repaired canonical installation,
pass independent source/runtime/browser checks, complete a business iteration
and a source-only refactor, and preserve their resulting graph changes and
captures. Product scenes and their final export follow those gates. The ledger
retains P7 as `in_progress` until that complete evidence exists.

[Repair 06](repair-06/README.md) moves presentation-file reads outside the event
admission lock. Its complete regression passes; native recording throughput
remains under investigation and is not accepted by this component receipt.

[Repair 07](repair-07/README.md) adds bounded HTTP event batches using the same
atomic reducer as local capture. Its full regression passes, and the native
trial completed one recording. A later recording remains interrupted; original
evidence and that distinction are retained in the repair receipt.

[Repair 11](repair-11/README.md) checks every submitted intermediate canonical
snapshot through the same admission reducer as live capture. It reproduces a
previously passing trial whose final SQL projection was correct but whose
same-version pre-state context contained a newly computed permission result.
Context/input guidance and the persisted iteration plan now keep these roles
explicit. Native recording, the semantic iteration and source-only refactor
remain required after the repaired candidate passes its complete gates.

[Repair 14](repair-14/README.md) retains the next incomplete native recording and
corrects two shared throughput problems: an undersized group wire budget and
repeated validation during discussion polling. A separate producer process is now
required in remote-load diagnosis. The full regression passes, and the maintained
implementation records all 3260 diagnostic events and 106 frames with an ordinary
stop. These derived inputs remain diagnostic evidence; both native trials and
their iteration/UI acceptance are still pending.

[Repair 15](repair-15/README.md) retains the first complete Python native recording
on repair 14 and its independent desktop checks. It also fixes state-model
folding shared by 2D/3D and records the naming and readiness findings. Node native
recording, both iterations, refactors and the final acceptance remain open.

[Repair 16](repair-16/README.md) separates effect-attempt completion checks,
retains commits and rollbacks with their actual owners, and clarifies custom
native policy event contracts. Original Node diagnostics and the controlled
adapter repair comparison remain archived. Its full regression, fresh install
and clean export passed; the remaining native trials and iterations stay open.

[Repair 17](repair-17/README.md) retains the complete Python native recording and
the subsequent viewer startup failure. Design and runtime viewers now share
bounded static-asset connection reuse. Independent desktop checks pass against
the original recording; final native capture still requires both applications
to upgrade normally, with nonempty live history for observer-exclusion checks.

[Python initial acceptance](python-initial-repair17/README.md) freezes the complete
native run and independent live-observer desktop checks before the simulated
user's cancellation request. This initial acceptance does not close P7.

[Repair 18](repair-18/README.md) preserves the Node native SQLite replacement
failure and OS-backed reproduction. It adds explicit complete-image collection
for atomic file publishers, retaining ordinary transactional/WAL behavior and
all catalog checks. Final trial captures, iterations and source refactors remain
separate acceptance requirements.

[Repair 19](repair-19/README.md) preserves Node's normally stopped recordings and
the subsequently failed full verification. It adds explicit native-evidence
export, original snapshot retention and per-producer tracing health. The trial's
stale live policy fingerprint is a separate bootstrap defect; old records remain
unchanged. Complete trial acceptance is still pending.

[Repair 20](repair-20/README.md) retains passed Node native captures and the subsequent independent Timeline rejection. API replay identity now follows the actual API projection, while real source/model/interface changes still invalidate old recordings. A fresh package passed complete regression; the projects must upgrade and recapture before final acceptance.

[Repair 21](repair-21/README.md) retains the Node native Timeline duration failure. Independent producer clocks now keep measured intervals despite interleaved batch delivery; time-window loops select exact event IDs without rewriting replay order. True clock reversals remain explicit. Native trial recapture and complete desktop acceptance remain pending.

[Repair 22](repair-22/README.md) retains the Node queue overflow and isolated diagnostics. Source inventory reuses unchanged excluded JavaScript findings and avoids redundant ordinary Windows path resolution while retaining link checks. Full regression and fresh installation passed; native transport sizing and complete P7 acceptance remain open.

[Node initial acceptance](node-initial-repair22/README.md) retains the subsequent
complete native run, stopped recordings, full verification and independent
desktop acceptance. Its finite native queue is explicitly sized to the measured
trial workload. The original fields, cases, deadlines and capture-gap checks
remain. Python's cancellation iteration, Node's semantic change, both source
refactors and final product scenes are still required before P7 closes.
