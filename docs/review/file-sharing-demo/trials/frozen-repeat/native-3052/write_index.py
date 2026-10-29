"""Write the English review with explicit local-private evidence boundaries."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
read = lambda path: json.loads(path.read_text(encoding="utf-8-sig"))
s, c, r = [read(OUT / name) for name in ("summary.json", "controls/report.json", "resources.json")]
t = r["host_reported_token_delta"]
text = f"""# Independent native control-fix acceptance: 3052e03

This isolated project's acceptance passed at frozen source `{s['canonical_revision']}`. It is automated technical acceptance using authorized **scripted user** inputs, not independent human confirmation or production acceptance. No business behavior, state/policy declaration, original test, expectation or canonical tool was patched. No shim, cross-chat message, publishing or promotion-page work was performed.

| Identity | Accepted value |
|---|---|
| Candidate | `{s['candidate_id']}` |
| Build | `{s['build_id']}` |
| Actual stopped recording | `{s['recording_id']}` |
| Source ZIP SHA-256 | `{s['source_bundle']['sha256']}` |

## Native upgrade and project checks

The native begin → plan/apply → provenance review and architecture seal → scan/inspect/review/verify/accept/check workflow passed. Only `conversation-controls.js` and `viewer.js` changed in the 196 installed managed files. All managed hashes match the frozen clean source; a subsequent native upgrade plan has zero changes/conflicts. The 50 protected files, 29 pre-existing test/review scripts, entire project declaration, state machine and policy network remain byte-identical. [Parity](parity.json), [byte comparison](byte-comparison.json), [native plan](plan.json), [review](../../.stategraph/framework-upgrade-3052e03/review.json), [final current check](current-check.json).

The original complete gate ran once: **35 pytest cases** in {s['pytest_seconds']:.2f} seconds, **84 scenario/mode runs**, **282 assertions**, {s['mapping_witnesses']} mapping witnesses and {s['projection_checks']} projection checks. Mapping, state constraints, business and project-test reports all pass; enabled-mode observations contain {s['enabled_mode_events']} events. The unchanged original evidence audit passes all **10 negative controls**. [Formal gate](gate-verify.json), [gate transcript](gate.stdout.txt), [audit](evidence-checks.json), [summary](summary.json).

## Actual scoped conversation controls

The native CLI used the real current chat identity and this project's canonical path. Native inspect supplied **117 nodes and 228 relations**; no identities were borrowed from another example. The project uses `policy:access_allowed`, whose canonical parent is `policy:network`. Every plan is retained intact. CLI publish alone was never counted as success: each check required the real browser's `applied` acknowledgement and independently checked **all plan.node_ids** in its semantic DOM.

| Authorized scripted operation | Observed result |
|---|---|
| Main business flow | 13/13 requested nodes visible; native adjacent policy/data boundaries retained |
| Download action, rules and parameters | 14/14 requested nodes visible, 13 actual guard/data relations retained, 38 generated capture fields visible |
| Policy ancestry | `policy:network` restored from the canonical declaration and expanded; checked after reload |
| Exact-recording permission filter | 124 of 429 actual events selected; native checkbox IDs equal the plan's raw event IDs, next stays inside the filter, loop and reload pass |
| Native 2D/3D | Every requested replay node remains visible in both modes |
| Explicit source selection supplement | Actual `FileService.authorise` source-ast child of `download` becomes visible, canonical parent expands and advanced details enable; authorized replay then restored |
| Missing `/vibelens` prefix | Native apply exits nonzero with its explicit-prefix error; private view revision/entries unchanged |
| Observer isolation | 0 new business events; global preference document and raw recording unchanged |

Inputs and provenance are in [original Chinese record](dialogue.zh-CN.md) and [scripted provenance](controls/provenance.json). [Control report](controls/report.json), [source selection](controls/source-selection-report.json), [missing-prefix result](controls/missing-prefix.view-write-check.json). The initial status rejected an unactivated native control session; the explicitly adopted Skill was then activated using a documented scripted wrapper. This was not represented as new human confirmation.

The first harness failed to parse because of an extra parenthesis. Its first live run then completed both native applies but stopped on an incorrect **test-harness** module URL. Both failures are retained under `controls/harness-syntax-error.txt` and `controls/attempts/harness-asset-route/`. Only the new harness syntax/asset route changed; native plans, framework, declarations and assertions were not weakened. The corrected complete run and supplementary source check pass.

## Source, recording and viewer regression

The byte-identical strict keyboard test passes the original path: newly select `revoke` → Shift+F10 → Source → focus returns. No post-selection rerender or alternate menu was used. Live and replay checks retain the complete 299-line source and 39 highlighted lines (250–288), with actual response/build identities and obsolete-recording source rejection. The native detail panel and its version checks are unchanged. [Strict test](keyboard-source-acceptance.json), [complete-file/highlight details](keyboard-details.json).

The new real current-build chain records **429 events and 11 snapshots**, with **0 errors, drops or gaps**, and drains in **{s['drain_seconds']:.3f} seconds**. All 21 Boolean composite evaluations are checked against actual same-check data dependencies. Positive guard animation and anonymous short-circuit evidence distinguish used rules from two skipped children; no skipped event is fabricated. Authorization view, 2D/3D, source, replay and reload pass. [Capture](browser-native/capture-report.json), [viewer](browser-native/report.json), [recording](browser-native/recording.json). Observer interactions add no business events.

Historical drain measurements **363.125 s** (V2), **53.775 s** (b78) and **121.584 s** (3458366) remain preserved. These differing workloads and schedules do not establish a throughput improvement or real-time performance acceptance.

## Preservation and privacy

The previous 3458366 success and b78 failure are unchanged. **9 historical ZIPs** stay at their original relative paths with verified hashes; **9 prior raw recording files** are unchanged. A new 94-file receipt ZIP contains **no ZIP members**. This prevents recursive archive growth without deleting previous source, diagnostics or records. [Previous-evidence index](previous-evidence-index.json), [preservation audit](preservation-check.json), [prior receipt ZIP](prior-3458366-receipts.zip), [current 250-file source ZIP](upgraded-source.zip). These packages do not include the newly created private control/view configuration.

**Only local raw evidence was prepared. No public evidence export was created.** Native control replies, saved private preferences and profile identifiers under `controls/` contain private session material. Before public/main-repository archival, exclude `bo_stategraph/config/control` and `bo_stategraph/config/views/conversations`, redact actual `vl_session`/session tokens and token-derived profile prefixes, and retain original hashes plus session fingerprints. Do not treat raw control files or this whole review tree as a publishable ZIP. Business values and node/event/build identities must remain unchanged. The main archive owner will handle this boundary.

## Source receipt and separate maintenance resources

The supplied complete source-repository `tools/verify.py` receipt was checked against clean frozen HEAD, all **240 Skill hashes**, two example receipts and full-log SHA `1692d98a0b72c2ccaddd65cedeb25bbb72c4112a8fa8cdd90c8587ec57bce697`. It is separate from the independent project/browser checks above. [Receipt validation](upstream-receipt-check.json).

At the recorded accounting snapshot, this maintenance window spans **{r['wall_seconds_authorization_to_snapshot']:.3f} seconds** from its authorization. The host cumulative-counter difference is input **{t['input_tokens']:,}** (cached subset **{t['cached_input_tokens']:,}**, uncached **{t['uncached_input_tokens']:,}**) and output **{t['output_tokens']:,}** (reasoning subset **{t['reasoning_output_tokens']:,}**). These are repeated-context host counters, not unique text or billing. The last available counter baseline predates authorization and can include earlier unreported work; final unreported tools/answer usage is excluded. Prior business and framework-round accounting remains separately referenced. [Exact accounting scope and timestamps](resources.json).

The accepted scope is complete. Services remain local on app port 8840 and graph port 8841; the private scoped URL is retained only in local raw activation evidence. No additional business, publication or demo-page work follows this round.
"""
(OUT / "index.md").write_text(text, encoding="utf-8")
print("Wrote current English acceptance index; no session token embedded.")
