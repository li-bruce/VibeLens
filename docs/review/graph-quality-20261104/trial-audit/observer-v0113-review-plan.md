# Independent v0.11.3 trial review plan

Status: preparation only. The existing trial is idle on managed v0.11.2; the
v0.11.3 candidate has not been installed in it. The planned Skill tree is
`2df145bcd7839014c9382029723f43bc6e0dd3c6`.

This plan reads existing files and receipts. The parent conversation will
authorize installation and start the upgrade turn. The independent review will
not run application, upgrade, acceptance or business commands.

## Upgrade preservation

Take a fresh baseline immediately before the authorized upgrade. The current
read-only preflight finds 21 recording JSON files, six configuration JSON files
and their locks, and 162 authored nodes. Retain every recording, including earlier
interrupted/extra attempts; the previous phase's count of 18 is not the new
baseline count.

Compare the following against that baseline:

- Owned business source and contracts, including the project-owned workflow,
  policy and machine definitions; all existing node and edge identities.
- Every existing full recording and historical baseline/acceptance phase.
  Native active pointers and a newly accepted phase may advance through their
  normal commands; prior accepted evidence must not be overwritten.
- Default/peer view files, existing main/business positions and pins, plus the
  active conversation's custom view, filters, aliases and replay selection.
  Managed upgrade itself should preserve them. Later native UI operations may
  change only the specific current-conversation fields they exercise.
- Installed candidate provenance and managed-runtime parity. A version string
  alone is insufficient: compare the candidate's files and the actual managed
  files. Label commit-pinned candidate installation separately from a published
  GitHub tag until tag parity is established.

The current default-view SHA256 is
`d180e12cf1cd913b29c4c1bf0febcf7ec6d9a8ce6c335ad5ff4b502b0c5306d9`.
Its earlier 16-leaf change remains unattributed; do not restore it or reinterpret
that historical failure when taking the new baseline.

## Missing observer-only UI measurement

Measure this in an actively recording, otherwise idle application:

1. Start full capture through the observer and wait for its actual recording
   response. Save the build/model/API identities and starting business-event
   count.
2. Use the exact conversation-scoped viewer. Operate native view selection,
   layer visibility, 2D/3D, camera, graph expansion and source inspection. Open
   and close Timeline where available. Avoid application actions and replay
   switching that would end or replace this active capture.
3. Wait for the actual private-preference save acknowledgement, stop and drain
   capture, then compare the ending event count and stored recording. Require
   zero added business events and no recording gap. Retain the action list and
   actual network request classification; application business requests should
   be absent during this observer-only interval.
4. Report `checks.viewer_controls_no_business_events` only from that measured
   result, with before/after counts, recording identity and the observed action
   list. This is the explicit field missing from the v0.11.2 browser schema.

Record an empty result honestly. A stopped recorder, an unchanged replay file,
or an absent observer-source ID alone cannot establish the active-capture
measurement. Source/module exclusion and the negative acceptance suite remain
separate checks.

## Fresh operation, replay and animation

Use one actual synthetic-account share and recipient read after native
acceptance. Bind the complete new recording and selected replay to the same
accepted candidate/build, model hash and API revision. Preserve the full record
while selecting the intended occurrence. Verify real HTTP statuses, observed
fields, lifecycle start/end and causal links.

Exercise the fixed animation path in the real application as practical: keep a
Timeline causal link visible while its graph edge is omitted/hidden, and keep
the same raw event selected through more than 1.1 seconds of native frames.
Motion must continue after that first cycle; compare actual connector pixels
and verify unchanged raw identity. A test with a graph transfer still present
does not exercise this specific failure. The standalone registered-lifecycle
regression already has its own three-run proof; do not relabel it as the new
application's execution.

Capture focused 2D, genuinely tilted 3D and zoomed Timeline views. Confirm saved
selection after server acknowledgement and reopening. Preserve first attempts,
including any acknowledgement race, before retaining the final run.

## Independent audit and public materials

After the upgrade turn is complete, reuse `audit_accepted_trial.py` with the
actual active phase and explicit receipt paths. Independently compare source
hashes, accepted candidate/build, observation receipt digest, current strict
API/docs revisions, layer/static counts, new recording digest and old-file
preservation. Report mapping, state rules, project checks and business assertions
separately. Missing or stale proof remains pending; do not change receipts to
fit the auditor.

Write a new phase directory and output basename. Copy only selected screenshots
and safe finite receipts with source SHA256 values. Exclude databases, uploads,
complete event recordings, private preference contents, credentials and cookies.
Export the completed public dialogue with `export_trial_dialogue.py`, identify
the agent-simulated user answers, redact every real `vl_session` URL capability,
and retain original-export SHA256, sanitized SHA256, replacement count and rule.
The original local session remains unchanged. Do not overwrite or rewrite the
committed historical dialogue/evidence.
