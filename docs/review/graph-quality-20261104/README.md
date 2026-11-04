# Graph quality review — 2026-11-04

Initial branch: `fix/graph-observation-quality`.
Source-boundary patch: `fix/source-scope-reserved-boundaries`.
Timeline follow-up: `fix/timeline-inspection-settlement`.
Baseline: `7f7907d2`; protected business/state engines remain unchanged.

## Scope and status

| Area | Evidence | Status |
| --- | --- | --- |
| Visible containment and interaction | [Geometry review](enclosure/README.md), [real Chrome interaction](browser/final-05-legacy-focus/results.json) | Passed: tight groups, perspective dragging, captions, filtering/restoration and hidden projections. |
| Concrete API and source explanations | [API review](api/README.md), [exact observation follow-up](api-observation-review.md) | Static discovery, source documentation, exact HTTP qualification and Chrome recording replay passed. |
| Source proximity inside type clusters | [Layout review](layout/README.md) | Focused and real browser checks passed. |
| Data operations | [Runtime check](data-operations-01.json) and [observer exclusion](observer-exclusion-01.json) | Passed; queries/transactions/transformations retain their distinct purpose. |
| Live databases | [First run](live-database-01.json), [retest](live-database-02.json) | Retest passed with the dedicated PostgreSQL, MongoDB, Redis and Neo4j fixture healthy. |
| Managed examples | [Current managed-example review](managed-examples.md), [clean export](clean-staged-export-timeline-inspection-0113-report.json) | Both v0.11.3 native candidates passed; 682 frozen inputs match Git. |
| Full repository | [Current host gate](full-verification-11-timeline-inspection-host.json), [patch review](../release-v0.11.3/README.md) | Passed locally, including databases, strict native checks and independent observer-free packages. Remote publication checks are recorded separately. |
| Fresh development dialogue | [Current trial review](trial-audit/README.md), [visible v1 dialogue](trial-audit/dialogue-v1/dialogue.md) | V1 and the sharing-note iteration completed. Focused controls and the next managed patch upgrade have separate current results. |

Data structure describes databases, tables/collections and fields. Data operations
records reads, writes, transactions and transformations, including selected
values, durations and committed/rolled-back outcomes. Function/source layers show
the implementation. These are related views of different facts; the operation
layer remains useful and is retained. Observer metadata queries remain excluded.

The review separates business correctness, state constraints, mapping and source
explanation completeness, and browser/runtime mechanics. Failed runs are retained
under separate names. Existing checks stay required. No human acceptance is claimed.

The two browser suites use real Chrome and canonical viewer assets. Their graphs
and serialized request facts are deterministic fixtures; they verify rendering,
dragging, replay and causal ownership. They are not evidence of a newly developed
application or real HTTP traffic from that application. The managed examples,
live database fixtures and backend tests have separate reports. In particular,
[API snapshot tests](api-snapshot-native-gate-retest.json) verify source discovery,
recording snapshots and rejection of invalid mappings, without executing Flask
requests. The [fresh-chat review](trial-audit/README.md) records actual application
development and the sharing-note iteration separately. Final focused viewer
controls and the next managed patch upgrade have their own current status there.

New projects require both source explanations (`bo_code.py docs --strict`) and
HTTP observation coverage (`bo_code.py api-check --strict`) in each coding
batch's verification entrypoint. These checks report different facts: comments
must come from the mapped source; API lifecycle projection requires the actual
handler, method, route and registered capture identity. Existing business, state,
source mapping and runtime checks remain required. Static route discovery is
limited to supported literal framework registrations; dynamic or chained router
construction still needs an adapter or explicit source binding.

The dynamic-layer path projection document from the preceding research branch
is still a proposal and is not presented as an implemented feature in this release.

The [v0.11.3 review](../release-v0.11.3/README.md) follows two failures in the
v0.11.2 post-publication browser jobs. One was a test persistence-acknowledgment
race; the other was an actual paused Timeline animation defect. Their original
receipts, controlled reproductions and fresh repairs remain separate.

## Failures kept for review

- The first complete gate detected an existing label-containment requirement:
  tight circles must still contain their visible child labels. The original
  assertion remains in force. See [the failed full gate](full-verification-01.json).
- The second complete gate detected a source-inventory regression: an externally
  supplied router's callback registration lost its original entrypoint fact.
  Generic callback registration and proven HTTP endpoint metadata now remain
  separate. The original multilanguage test is unchanged; a new case checks
  both retained callback evidence and the absence of an invented API endpoint.
  See [the second full gate](full-verification-02.json).
- The third complete gate detected a legacy focus-selection regression in the
  unchanged layered-view test. Older endpoints without observation metadata
  can again locate their capture owners through handler mappings for focus
  selection. This compatibility does not activate an endpoint or invent an
  HTTP duration. New endpoints with an explicit observation-source array,
  including an empty one, use only qualified capture IDs. See
  [the retained failure](full-verification-03.json) and the final
  [geometry interaction](browser/final-05-legacy-focus/results.json) and
  [API replay](browser/api-observation-05-legacy-focus/results.json) reruns.
- The first live-database run began before the dedicated Compose fixture was
  running. Its connection failures are retained. The second run passed after
  all four containers became healthy; no database check was relaxed.
- Managed architecture seals rejected the deliberately rebuilt routing bundle.
  Its reviewed D3 export has a new exact hash. Approval updates only that
  distribution's pins; business source, state engines and independent
  expectations stay protected.
- The version update initially linked a missing review index. The package
  check caught the missing target; [the retest](package-copies-02.json) passed
  after the release index was added.
- Final cross-layer review found that separating technical capture anchors
  from physical endpoints initially removed HTTP lifecycle intervals from the
  API layer. A generic source link could also mark another route sharing the
  same handler. Release preparation stopped for an exact, shared API observation
  projection and independent recording-context checks. This is a product defect,
  separate from the passing static API and documentation checks. The correction
  retains native event/call/parent IDs, projects only source-qualified HTTP
  observations, isolates routes sharing a handler, and keeps concurrent GET/POST
  intervals separate. Invalid selectors and reused capture identities fail the
  strict API gate; source-only functions remain static. Unit, snapshot and
  actual Chrome replay checks now pass. See [the follow-up](api-observation-review.md).

## Release gate

The [source-boundary follow-up](source-scope/README.md) records the explicit
owned-source/dependency/output declaration, initial Skill guidance, retained
scope failures and actual directory-traversal measurements. The original full
project discovery guard and protected state engines remain in force.

The [initial release gate](final-release-gate.json) records v0.11.0's local checks.
The [v0.11.1 review](../release-v0.11.1/README.md) records the subsequent clock,
lifecycle, source-boundary and CI repairs, with a separate frozen candidate gate.
Remote CI, published assets and the independent dialogue retain their own results.
