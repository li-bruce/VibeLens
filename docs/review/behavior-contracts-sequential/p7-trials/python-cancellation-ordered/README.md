# Python drive: cancellation iteration

This review retains a complete native retest and the independent desktop checks
for the confirmed queued-task cancellation change. P7 as a whole is still open.
Formal `accept` and `check` both passed with current bindings. The two owned
services were then stopped; no source refactor or additional run followed.

Candidate: `85c8db3ad234e68240ccfeec053b62ce1d7f1d69926d8305114c4bd902620bba`.
Build: `788ab708c11a78be7bde19baab9ce5a45c6d684dcdf3f899689908329ec2015a`.
The installed Skill is the immutable `ordered-evidence-skills` package recorded in
[the installation receipt](../python-ordering-review/installation.json).
See [results and scope](results.json), [original native checks](native-checks.zip)
and [the accepted source/model snapshot](source-and-models.zip).

## Native results

The pre-recording and post-recording gates both passed their five reports:
mapping, state rules, project checks, business and concepts. The original business
suite retained 162 assertions, 21 business tests and 6 HTTP tests. The omitted
cancellation-completion negative control failed as required; the original evidence
passed before and after that isolated mutation. The original browser checks and
38 cancellation interface checks also passed.

| Recording | Actual execution | Result |
|---|---|---|
| `50f3abc53dc245eebe3bf06a286847f6` | Existing controlled native fixture; revoke commits before an explicit preparation call | 866 events, 24 frames, 304 closed invocations; 20 executed checks passed |
| `91bd56f0d2e243c7b393f83f42062093` | Ordinary application entry with its default background worker; admission commits before revoke | 3,167 events, 26 frames, 594 closed invocations; 19 executed checks passed |

Both recordings stopped normally with their fixed producer prefix drained and no
capture gaps. Their native SQL, event and frame evidence remains separate.
The normal Stop acknowledged target/completed 3,261, with 16 later submissions
outside that fixed target still pending. It did not assert that later application
activity had stopped or that the entire producer queue was empty.

The normal recording proves the actual request's historical queued version and
the result required by its independently observed transaction order. It does not
prove that the task was still queued at revocation, that the automatic worker
rejected it, or that a rejected task stayed terminal. Those order-specific
properties have separate controlled evidence. The denied-input/current-context
case is explicitly unexercised in the normal recording. The controlled fixture
uses the real native service but does not prove automatic worker scheduling.

The original failed recording and the reason for correcting its race-sensitive
test premise are retained in [the ordering review](../python-ordering-review/README.md).
Application scheduling, confirmed business policy, queue capacity and timeouts
were unchanged for this retest.

## Independent desktop checks

[Original checks, runners and screenshots](desktop-checks.zip) are indexed by
[file hashes](desktop-checks.json). All five suites passed against the real service:

- Six English/Chinese reloads completed in 1.3–2.0 seconds without page errors.
- Seven layer views, their 2D/3D modes, expansion and source structure were checked.
- Timeline used the real clock: 667 lifecycle intervals, including 43 positive
  business intervals. The dragged time selection matched exactly 2,142 events.
- Graph flow arrows and node activity were checked in both rendering modes.
- Custom views, source navigation, group dragging, annotation and language
  switching were exercised through the actual controls.

The control suite began with 4,335 live events and ended with 4,431. No observer
request appeared in the checked event history, and all six native SQL tables were
unchanged. The increasing live count is retained; this is not a claim that the
background application produced no events. Actual updated preferences were kept.

Screenshots establish tested UI behavior, not a claim that an expanded full graph
is suitable advertising artwork. Focused product scenes and the final P7 matrix
remain separate deliverables.

## Manual readability finding

The rules screenshot exposes a generated alias omission:
`policy-operation:cancel_download` appears as
`源码元素 · policy-operation:cancel_download`; `Rules` also retains a generic
source-element prefix. The inventory/fingerprint checks and locale switch pass,
but those captions do not explain the concepts. The existing interface-language
guide already requires this review and explicitly separates it from mechanical
coverage checks. A later, separately recorded presentation correction must retain
IDs, definitions and personal names/notes. This finding remains open here; the
original screenshot and accepted native evidence are unchanged.
