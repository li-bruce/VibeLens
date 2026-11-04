# Independent file-sharing trial review

Trial: `VibeLensTrials/graph-quality-dialogue-20261104-01`.
Conversation: `01a1a511-0990-7ab0-b24b-3bdfb96b7b0b`.

The remark iteration has completed native verification: **126/126 business
assertions**, with mapping, state rules and project checks reported separately.
Its finite Chrome run reports **28 true checks**. This is AI-coordinated testing
with simulated user answers and synthetic accounts, not an independent human
usability study.

V1 used GitHub v0.11.0. The iteration used commit-pinned `c56fd19f`; its 305 Skill
files were verified identical to the later official v0.11.1 tag download in
[release installation parity](release-install-parity.json).

## Review index

- [Completed v1 audit](v1-completion-audit.md): the GitHub-installed v0.11.0
  application, actual HTTP observations, all nine layers and remaining visual
  checks.
- [Visible v1 dialogue](dialogue-v1/dialogue.md): original public messages and
  simulated user answers, with local paths normalized.
- [Remark iteration audit 02](remark-v2-independent-02-notes.md): current source
  hashes, accepted build, native categories, browser recording and retained
  global-revision flags. [Audit 01](remark-v2-independent-01.md) is preserved.
- [Exact revision proof](remark-v2-independent-02-revision-proof.json): manifest
  CRLF-to-LF normalization changes the full graph revision while parsed manifest,
  build and all eight physical API endpoint nodes remain equal.
- [Accepted v2 browser evidence](remark-v2/accepted-c56-01/browser-summary.json):
  selected screenshots and five native/strict receipt copies, with original
  file hashes. Raw event payloads, databases and credentials are omitted.
- [Visual review](remark-v2/accepted-c56-01/visual-review.md): observed strengths,
  crowded views and remaining focused-capture needs; no general usability pass.
- [Dialogue through the active control turn](dialogue-v2-controls-in-progress-01/dialogue.md):
  public conversation only. The final control outcome was still pending at
  export; all simulated answers remain identified as such.
- [State residence diagnosis](timeline-state-review.md): adjacent intervals
  reflect the same file's real successive states; no artificial duration added.

## Current follow-up

The conversation-control turn is still active. Custom views and recording
filters are being exercised through `/vibelens`; it reproduced rejection of a
same-build recording after manifest line endings changed the graph revision.
The rejection and its evidence remain preserved. The trial is refreshing strict
receipts and preparing a new recording before completing focused Timeline checks.
This follow-up is separate from the earlier 28-check browser run.

Fresh final receipts after those controls and the planned managed **v0.11.2**
upgrade are pending. Nothing in this index claims that upgrade or its native,
browser and recording acceptance has completed.

The [source-scope adoption fixture](source-scope-adoption/README.md) records the
initial directory-planning requirements and their targeted execution tests.

## During-generation snapshot

`snapshot-in-progress-01.json` is an independent read-only snapshot taken during
generation. It preserves hashes, declared parameters and source docstrings, span
identities, native drive calls and current project declarations. It imports no
application module, runs no business operation and changes no trial file.

At that historical snapshot, the domain service, SQLAlchemy models, neutral observer port
and project-owned state executor have authored implementations. The API server,
observation integration, launcher, model builder and tests remain explicit
placeholders. The graph declaration and empty implementation inventory still
represent the accepted design baseline. These are pending work, not failed
acceptance results.

The implemented service currently has source-backed descriptions of its core
methods and parameters. Share/revoke operations call the independent native
`bo_stategraph.workflow.advance` before committing database changes, and publish
observation after commit. Stable business span IDs include `login`, `upload`,
`view`, `share`, `revoke`, `download` and `transition`.

These placeholders were subsequently implemented and tested; use the completed
v1/v2 audits above for accepted-batch results. Initial released-version evidence
remains separate from later upgrades and retests.

Run `audit_snapshot.py NEW_PHASE` from the maintained repository to create an
additional snapshot. The script refuses to overwrite existing evidence.
