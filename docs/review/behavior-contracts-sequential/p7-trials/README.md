# P7 — Independent candidate trials

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

Before closing P7, both retests must use the repaired canonical installation,
pass independent source/runtime/browser checks, complete a business iteration
and a source-only refactor, and preserve their resulting graph changes and
captures. Product scenes and their final export follow those gates. The ledger
retains P7 as `in_progress` until that complete evidence exists.
