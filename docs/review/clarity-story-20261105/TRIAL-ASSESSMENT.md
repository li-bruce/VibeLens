# Completed independent trial assessment

Trial: `01a1a757-9d29-7500-966c-db0e29a7651b` (public v0.12.0, then managed v0.12.1 upgrade).

**Conclusion: the first application checkpoint is complete, but overall acceptance failed.** The conversation ending is not equivalent to the Skill passing every feature. Business behavior, mapping, recording completeness and formal delivery are separate results.

| Requirement | Evidence | Assessment |
| --- | --- | --- |
| Confirm business, state and rules before coding | C04 confirmation and concept-binding report | Passed for one native `file_review` machine. Three bound machines were explicitly rejected; no multi-machine support is claimed. |
| Implement the confirmed application | 93 configured assertions; 14 scenarios in each on/off/fault mode | Passed within the authored cases. Actual browser checks also covered upload, review, sharing, messages, download and revocation. |
| Map source, values, policy decisions and actual HTTP responses | Independent runtime assessor, documentation/API/source/database reports | Passed within configured Python and SQLite/SQLAlchemy coverage. Static dynamic-dispatch limits remain documented. |
| Keep business independent of observation | Off/fault runs, exported core HTTP checks | Passed. Queue pressure preserved business but lost 683 envelopes; that is a capture failure, not an observation pass. |
| Preserve state frames for replay | Stopped 1,073-event browser record and 381-event current-index record | Failed: both retain two pre-review state-frame gaps after successful producer drain. |
| Formal iteration acceptance | `verify-delivery.json`, `accept-delivery.json`, `check-delivery.json` | Failed at protected parameter coverage. Independent diagnostic passes do not override this gate. |
| Consistent recording eligibility | `replay-version-diagnostic.json` | Failed: an old recording remained listed after its API-index revision changed, but the viewer rejected reopening it. |
| Subsequent business iteration and automatic remapping | No later business iteration was performed | Not tested. Managed framework upgrade and stale-source detection are narrower evidence. |
| Every viewer interaction | Actual 2D/3D, Fit, Timeline, playback, recorded source | Partial. Exhaustive custom views, pin/drag/filter combinations and recovery were not accepted. |

## Causes and next corrective work

1. The first generated baseline described the derived Boolean `authenticated` as a redacted `password` output. Correcting the policy to `derived` replaces a protected parameter record and fails `weakened_feature_coverage`. The baseline lacks the requirement linkage used by the existing change exception. Improve initial capture-declaration validation and design an audited metadata-correction path; preserve requirements and coverage. Do not reset the baseline or weaken the checker.
2. The observation session treats a repeated native revision as a duplicate and omits a frame for a new evidence ID. A repeated state is still a new observation. Add a regression with distinct reads of the same native revision, preserving evidence association without inventing a transition. Historical missing frames remain unknown.
3. The recording catalog checks build/model eligibility while the viewer additionally checks API/concept revisions. Use one compatibility contract for listing and opening; show an explicit historic/incompatible result when appropriate. Preserve original source and facts.

These runtime corrections are recorded as open work, rather than concealed by the presentation redesign. The trial's installation, baseline and independent checks were not edited during this review.

## Evidence provenance

Original evidence: `VibeLensTrials/release-v0.12.0-dialogue/review/upgrades/RESULTS.md`, beside this repository. Selected reports and hashes are archived in `trial-evidence/`; the exported public dialogue is in `dialogue/`. The source trial distinguishes simulated requirement replies from actual browser operations.

## Implementation density

The existing viewer folds API entries, directories/files, static symbols and captured actions/values into one `implementation` plane. These are useful facts at different reading scales. Refine display into **Entry points → Project structure → Code execution**, retaining the common semantic implementation classification. Queries, transactions and their values stay with the executing code; storage schemas remain their own concern. This does not create duplicate nodes or fabricate runtime spans for files.

The default remains the three concept models. Detail is opened as needed, consistent with [C4's optional, focused code-level views](https://c4model.com/diagrams/code). Geometry is not a claim that every execution must traverse each layer.
