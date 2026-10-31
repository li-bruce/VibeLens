"""Index final original-project acceptance only after every required receipt passes."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/review/dialogue-acceptance-20261031"


def read(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def passed(name):
    value = read(name)
    if not value.get("passed"):
        raise ValueError("Final receipt did not pass: " + name)
    return value


def write_readme(summary):
    app = summary["actual_application"]
    trace = summary["actual_timeline"]["checks"][0]
    body = f"""# Independent dialogue and viewer acceptance

Status: **passed within the boundaries below**. The accepted original project
completed its first version, an ordinary business iteration, reviewed observer repairs
and independent browser retests. Earlier failures remain available for review.

- [Complete visible dialogue](dialogue-complete-002/dialogue.md)
- [Machine-readable result index](acceptance-summary.json)
- [Final accepted source and contract snapshot](iteration/original-v2-mime-before-browser/snapshot.json)
- [Final executed harnesses and hashes](scripts/followup/manifest.json)

## The actual trial

The real Codex conversation **VibeLens 生命周期全流程试用**
(`01a18f4d-11b3-7553-bbeb-6410929a9146`) developed a separate
Python/Flask/SQLAlchemy/SQLite team file-sharing application. Conversation was in
Chinese; maintained source and comments were in English. Accounts and files are
synthetic. The coordinator supplied explicitly marked simulated user replies;
later actual human corrections are preserved in the same transcript. This is a
real development conversation with a test persona, not an independent human study.

The first version confirmed login, upload, an owner-selected reviewer and recipient,
approval/rejection, three-party final notices, authorized download, pending
cancellation and immediate revocation of future downloads from an unchanged page
or old URL. The developer showed an inline graph and a reachable design Web page
before implementation. A coordinator reminder for the first inline graph is also
retained rather than presented as autonomous success.

![Confirmed initial business graph](design/confirmed-intent-draft.png)

The next request was an ordinary business change, without graph or probe reminders:
let the reviewer return an application for an explanation, then let the owner
resubmit it to the original reviewer. Necessary questions confirmed required
trimmed text up to 200 characters, repeated rounds, the latest pair only, private
text for the owner/reviewer, owner-only return notices and reviewer-only resubmit
notices. Existing final notices and participants remained unchanged. A later
ambiguous human reply triggered reconfirmation; the actual human explicitly kept
the previously confirmed rules. The developer updated the inline draft, state
declaration, policy branches, implementation bindings, probes and cases.

[Ordinary iteration gates and every matching attempt](iteration/ordinary-iteration-evidence.json)
preserve the first strict rejections, fixes, acceptance and checks.
[Nineteen independent structure checks](iteration/original-v2-structure-04/structure-and-data-update.json)
verify unchanged old baselines, cases, modes, required parameters, core identities,
updated source indexes, actual SQLite columns/state constraints and preserved old
rows/files. A real two-round run with an intentionally wrong observed length fails
mapping while native business behavior stays correct; the restored run passes
([control](iteration/original-v2-probe-value-01/supplement-probe-control.json)).

## Final original-project results

| Area | Result | Evidence |
| --- | --- | --- |
| Initial version: users, review, notices, exact download bytes, cancellation and stale-link revocation | Passed on the accepted original project | [Initial operation retest](operations-original-v1-optimized-01/results.json) |
| Business iteration: two return/resubmit rounds, private text, wrong actors, empty/201-character rejection, 200-character boundary, cancellation, rejection and final approval | {app['checks']} groups passed | [Final actual operations](operations-original-v2-final-02/results.json) |
| Recording the actual iteration | {app['recorded_events']} events, complete capture; stop took {app['stop_milliseconds'] / 1000:.3f} seconds at the unchanged 30-second bound | Same operation report and complete archived recording |
| Business, states, permissions, function/value, API, project/code, database and data-operation views | Required configured views have nodes and relations; unconfigured presets remain empty | [Preset observations](application-original-v2-final-02/preset-observations.json) |
| Names/identity, annotations, core marks, hide/show, expand/collapse, actual pointer pin/reload, full source, custom views, 2D/3D, layers and language | 12 groups passed | [Viewer checks](application-original-v2-final-02/viewer-results.json) |
| Personal filters, specific exclusions, pins, annotation and expansion across source updates | Exact saved values retained; old-build recordings leave the current list | [View retention](iteration/original-v2-mime-view-01/view-update.json) |
| Timeline lifetimes and directed handoffs | {trace['intervals']} intervals and {trace['routes']} same-layer/cross-layer routes | [Timeline checks](timeline-original-v2-final-02/results.json) |
| Waiting, resumption and approval in 2D/3D | Exact recorded event ID shared by graph, time ruler and selected step; four separate closed waiting periods | [Iteration state checks](timeline-original-v2-final-supplement-02/results.json) |
| Timeline zoom, ruler/keyboard seek, drag range, looping, cutoff depth, single layer, skip/restore, play/pause, Chinese/mobile and live return | Passed; saved recording bytes unchanged | Same timeline checks |
| Region-only recording and restoration of full capture | Passed with real approval and subsequent download | [Focused capture](focused-original-v2-final-02/results.json) |
| Viewer/source/layout/preferences operations | Zero new application events | Same viewer and timeline reports |
| Complete repository and real database checks | Passed with original checks retained | [Final verification](repository-mime-verification.json) |
| Existing UI regressions, including registered/mid-span lifecycles, data/code, recording controls, 3D, routing, clustering, layers and replay | 15 distinct suites passed after retained corrections | [Regression index](acceptance-summary.json) |

![Actual state residency and connected calls](timeline-original-v2-final-02/state-residency-and-calls.png)

![Actual pointer orbit and the same recorded timeline](timeline-original-v2-final-02/actual-orbit-and-timeline.png)

The visual proof reads the saved facts, uses native controls and a real pointer
orbit, and verifies the recording bytes are unchanged. Short calls retain measured
durations; zoom reveals them. Waiting/resident states retain their own intervals.
No duration or missing event is synthesized for the screenshots.

## Failures, repairs and retests

| Finding | Repair and retained evidence |
| --- | --- |
| The first project gate lacked implementation witnesses | The original baseline was retained and the missing actual evidence was added. All four categories then passed. [First failed gate](original-project-gate/verify-001.json), [initial accepted snapshot](iteration/original-v1-before-browser/snapshot.json). |
| Recording stopped before its asynchronous producer queue drained | Added bounded settlement before start/stop outside observer locks. An incomplete flush remains explicitly interrupted. [Original failure](operations-v1-initial/results.json), [capture audit](layer-and-capture-audit-v1.json). |
| Deferred Python HTTP result builders used a cleared exception variable and omitted six actual return observations | Fixed the real deferred builders and actual redirect status, then formally upgraded the original project. Native business responses alone no longer suffice for mapping acceptance. [Exact early copy repair](patches/http-capture.diff), [accepted original retest](operations-original-v1-optimized-01/results.json). |
| Selected recording scope did not reach the native producer; excluded data wrappers still extracted observer summaries | Connected scope/flush/health controllers and skipped excluded summaries while executing native work. [Scope failure/retest](focused-actual-retest/results.json), [data regression](data-scope-after.log), final focused capture above. |
| A global code-node budget removed API endpoints before the API filter ran | Select API neighborhoods before display limits. [Failed view](application-v1-api-failure/viewer-results.json), [source regression](code-api-regression.log), final live API view above. |
| Repeated source checks/parsing made recording drain exceed the unchanged bound | Kept fresh physical containment and byte reads, reusing canonical comparison only for already verified identical JSON bytes. [Two original failures](operations-original-v1-01/results.json), [accepted v1 retest](operations-original-v1-optimized-01/results.json). |
| The larger ordinary iteration again exceeded 30 seconds: 1,226 interval events saved, 111 still pending, with no drops/capture errors | Added optional bounded local Python event batches. Every event retains the same strict envelope/identity rules; source bytes are checked at both pre-publication boundaries. Snapshots remain FIFO barriers, invalid groups fall back to individual admissions, and the original callback path remains tested. [Original interruption](operations-original-v2-supplement-01/results.json), [isolated repair](operations-batch-sink-copy-02/results.json), final accepted original retest above. |
| Two full viewer runs stalled on a module connection during language reload | A cold TCP burst exposed the five-slot listener backlog: 10 of 16 connections timed out. The 64-slot backlog passes exact-byte/no-event checks. Full viewer and 12 repeated language changes then passed on the repair copy; the original-project full viewer also passed. [Failed browser run](application-batch-sink-copy-02/viewer-results.json), [before](viewer-transport-before.log), [after](viewer-transport-after-02.log), [copy reloads](reload-viewer-transport-after-01/reload-results.json). |
| A later original timeline run passed eight groups, then stalled on reload; a direct browser check also rejected streaming WASM | The WASM header incorrectly included a text charset. Shared `bo_content_type` now keeps binary MIME exact; runtime, design and shipped adapters share that policy and `BOHTTPServer`. Native/header checks and actual streaming compilation pass. Repeated full timeline tests retained all assertions and later passed. [Retained timeline failure](timeline-original-v2-final-01/results.json), [actual failed compilation](original-transport-diagnostic-01/transport.json), [native failure](viewer-wasm-before.log), [native repair](viewer-wasm-shared-after.log), [successful compilation](copy-wasm-streaming-after-01/transport.json). |
| The ordinary iteration's new spans/instance identities were incomplete; generated reason text rewrote protected old definitions | Existing source, parameter and instance checks rejected the candidates. The developer fixed bindings and restored exact protected definitions; old cases/modes were retained. All attempts remain in the ordinary-iteration archive. |
| A question premise assumed retained round history | The persona corrected it to the latest pair. Guidance now asks whether an old rule applies before asking about its audience. This wording is a usage-derived correction, not a separately repeated forward dialogue experiment. |

The observer repairs were separate reviewed changes after the accepted business
iteration. [Technical upgrade history](iteration/technical-upgrade-evidence.json)
retains their independent baselines, source parity, actual recordings, strict
checks, observer-free package runs, original-test preservation and final data/file/
recording/preferences conservation. The final [MIME upgrade](iteration/mime-upgrade-evidence.json)
and [native observation attempts](iteration/observation-attempts-evidence.json)
remain separate archives. No failed baseline was reset to obtain a pass.

Tests also rejected missing instances, stale revisions, missing context/witnesses,
capture errors, missing actual returns and source-only edits/new functions. See
[six evidence controls](iteration/original-v1-negatives-02/negative-controls.json),
[real wrong-value control](iteration/original-v1-probe-value-01/probe-value-control.json)
and [source-only controls](iteration/original-v1-source-01/source-only-controls.json).
[Harness corrections](iteration/harness-setup-failures.md) distinguish test setup
mistakes from application defects; their failed runs remain available too.

## Performance and boundaries

On the same native Windows host, model and 46 source files, admission of 100 actual
event envelopes measured 14.70 ms/event with the ordinary sink and 3.16 ms/event
amortized with groups of 16. This is a receiver microbenchmark, separate from the
actual complete recording above. [Before](ingress-original-v2-host-before/results.json),
[batch](ingress-original-v2-host-batch/results.json). A Windows-handle alternative
showed no improvement in a fair host comparison and was reverted; its experiment
and decision remain under `experiments/windows-handle/`.

- Historical recordings currently disable optional project/AST/API indexes because
  those indexes are not snapshotted. Live navigation passed separately. Bound
  handler source and captured facts remain available during replay; tests explicitly
  verify the disabled state instead of loading current indexes into old facts.
- The independent application conversation is Python. Node/React/Vue parsing,
  adapters and other database families have repository regressions. This run does
  not claim another new application conversation for those stacks.
- Shared-resource concurrency, joins and shared membership are not configured in
  this simple application. Existing repository examples and fixtures cover them.
- Runtime evidence establishes the observed runs. Unresolved static calls remain
  unresolved; static relations do not become executed calls.
- One retained custom view reported 31 blocked routes at startup
  ([actual diagnostic](original-wasm-streaming-final-01/transport.json)). Relationship
  and capture checks passed; obstacle-avoidance quality for that saved layout was
  not established by the fixture routing results.

## Review and reproduction

The original local project is `VibeLensTrials/lifecycle-dialogue-20261031` beside
this repository. Its current process/build information and URLs are in
`review/runtime-process.json`. The original application is left available for
inspection; owned repair-copy services were shut down after their tests.

Source/contract ZIPs retain file hashes and the actual observation command output.
The final [after-browser snapshot](iteration/original-v2-mime-after-browser/snapshot.json)
retains the current view/records without changing application source. Earlier
failed/superseded checkpoints remain in [checkpoint history](checkpoint-history/index.json).
Large event/view JSON is losslessly stored as gzip, with original hashes in
`compressed-evidence.json` and `followup-compressed-evidence.json`.

Restore the [final executed harnesses and review helpers](scripts/final/manifest.json)
under `.validation/` for their relative imports. Final successful harness versions
are hash-indexed; notes identify earlier harness corrections. The trial launcher
copies the original application into an isolated repair project; its results are
always labeled separately from accepted original-project evidence.

Run repository checks from the root with its Python environment and a configured
Playwright browser:

```powershell
.venv/Scripts/python.exe -B -X utf8 tools/verify.py --database
.venv/Scripts/python.exe -B -X utf8 tools/check_source.py --format
.venv/Scripts/python.exe -B -X utf8 .validation/audit_dialogue_archive.py review-repeat
```

Mapping, state constraints, business correctness and project checks remain
separate reports. A faithfully displayed application bug may pass mapping and fail
business checks; an incorrect observed value must fail mapping even when native
behavior is correct.
"""
    (OUT / "README.md").write_text(body, encoding="utf-8")


def main():
    repository = read("repository-mime-verification.json")
    assert repository["valid"] and repository["exit_code"] == 0
    assert hashlib.sha256((OUT / repository["log"]).read_bytes()).hexdigest() == repository["sha256"]
    for name, expected in repository["tested_files"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
    quality = read("source-quality-mime.json")
    assert quality["valid"]
    latest, attempts = {}, []
    for name in ("regressions-final/suite-results.json", "regressions-final-retest/suite-results.json"):
        value = read(name)
        attempts.append({"receipt": name, "passed": value["passed"]})
        for case in value["cases"]:
            latest[case["name"]] = {**case, "receipt": name}
    assert len(latest) == 15 and all(case["exit_code"] == 0 for case in latest.values())
    phase = "original-v2-final-02"
    operations = passed("operations-" + phase + "/results.json")
    viewer = passed("application-" + phase + "/viewer-results.json")
    timeline = passed("timeline-" + phase + "/results.json")
    supplement = passed("timeline-original-v2-final-supplement-02/results.json")
    focus = passed("focused-" + phase + "/results.json")
    retention = passed("iteration/original-v2-mime-view-01/view-update.json")
    structure = passed("iteration/original-v2-structure-04/structure-and-data-update.json")
    wrong_value = passed("iteration/original-v2-probe-value-01/supplement-probe-control.json")
    streaming = passed("original-wasm-streaming-final-01/transport.json")
    conservation = passed("iteration/original-v2-final-preservation-01.json")
    accepted = read("iteration/original-v2-mime-before-browser/snapshot.json")
    business = read("iteration/original-v2-before-browser/snapshot.json")
    assert accepted["accepted"]["build_id"] == accepted["build_id"]
    summary = {
        "overall": "passed within the explicitly listed replay and language-trial boundaries",
        "repository": repository,
        "source_quality": {"valid": True, "python_modules": quality["python_modules"],
                           "javascript_modules": quality["javascript_modules"], "receipt": "source-quality-mime.json"},
        "browser": {"latest_passed": True, "unique_suites": len(latest), "attempts": attempts, "latest": latest},
        "independent_conversation": {
            "thread_id": "01a18f4d-11b3-7553-bbeb-6410929a9146",
            "title": "VibeLens 生命周期全流程试用",
            "status": "completed",
            "dialogue": "dialogue-complete-002/dialogue.md",
            "provenance": "Real Codex development conversation with explicitly marked simulated user replies and preserved actual human corrections.",
            "ordinary_business_iteration": {"accepted": business["accepted"], "structure_checks": len(structure["checks"]),
                                             "receipt": "iteration/ordinary-iteration-evidence.json"},
            "final_observer_upgrade": {"accepted": accepted["accepted"], "receipt": "iteration/mime-upgrade-evidence.json"},
        },
        "actual_application": {"passed": True, "scope": "Accepted original conversation project after formal upgrades; not a copied candidate",
                               "checks": len(operations["checks"]), "recorded_events": operations["recordedEvents"],
                               "stop_milliseconds": operations["stopMilliseconds"], "receipt": "operations-" + phase + "/results.json"},
        "actual_viewer": {"passed": True, "groups": len(viewer["checks"]), "receipt": "application-" + phase + "/viewer-results.json"},
        "actual_timeline": timeline,
        "iteration_waiting_timeline": supplement,
        "focused_capture": focus,
        "view_retention": {"passed": True, "groups": len(retention["checks"]), "receipt": "iteration/original-v2-mime-view-01/view-update.json"},
        "semantic_probe_control": {"passed": wrong_value["passed"], "receipt": "iteration/original-v2-probe-value-01/supplement-probe-control.json"},
        "native_wasm_streaming": {"passed": streaming["passed"], "result": streaming["streaming"], "receipt": "original-wasm-streaming-final-01/transport.json"},
        "post_operation_conservation": {"passed": conservation["passed"], "checks": len(conservation["checks"]), "receipt": "iteration/original-v2-final-preservation-01.json"},
        "limits": [
            "Historical recordings do not snapshot optional project/AST/API indexes; those controls remain disabled during replay. Live source-index navigation passed separately.",
            "The independent new application conversation is Python/Flask/SQLite. Node/React/Vue and other databases have repository regressions, not a second new application conversation in this run.",
            "This application does not configure shared resources or concurrent Petri-style activities; those remain covered by repository examples and fixtures.",
            "The narrowed question-premise wording is a usage-derived guide correction, not proof of a new forward dialogue trial for that wording.",
            "One retained custom view reported 31 blocked routes at startup. Relationship/capture checks passed; obstacle-avoidance quality for that saved layout remains a separate visual-quality finding.",
        ],
    }
    export = OUT / "clean-export-final-followup.json"
    if export.exists():
        value = read(export.name)
        assert value["valid"]
        summary["clean_export"] = {"valid": True, "receipt": export.name, "revision": value["revision"],
                                   "scope": value["scope"]}
    (OUT / "acceptance-summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    write_readme(summary)
    print(json.dumps({"passed": True, "events": operations["recordedEvents"], "viewer_groups": len(viewer["checks"]),
                      "browser_suites": len(latest), "timeline_groups": len(timeline["checks"])}))


if __name__ == "__main__":
    main()
