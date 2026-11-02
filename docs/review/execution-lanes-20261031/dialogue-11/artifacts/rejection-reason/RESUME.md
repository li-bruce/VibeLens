# Rejection reason handoff — 2026-11-01

The authorized reason feature is complete. Wait for the next ordinary business requirement; add no further feature. Read project AGENTS and `coverage.md` before continuing. VibeLens is explicitly active only for this conversation/project. Business dialogue is coordinating-AI simulated, not independent human acceptance.

## Confirmed scope

U006: "审核拒绝时填写原因，上传的人在详情里看得到；通过不用填。"

U007: "对，就按这个理解做。拒绝原因保留原文，上传的人能在文件详情里看到，通过时不用填写。"

The displayed graph and exact confirmation are retained in `dialogue.json`, discovery sources and design preview. Existing role, directed sharing, withdrawal and terminal-state decisions remain. SQLite, Python and drive mode are reused. No new state, resubmission path, account system or service is added.

## Identity and gates

- Change: `.stategraph/rejection-reason-20261101`.
- Candidate: `5e2eb174f52bfe298eb67c91ace11a6b3a16d3fc1464ee9cff3e30cfb9166dfc`.
- Actual build: `4018f48c5c6ced418560820853dfb11b182adb4fd7fee5bfdf3671f7c41b07e1`.
- Baseline starts from the exact previous accepted withdrawal candidate `bfd9632113b00302ce0b0b0a9594864e3928b4a0e435d7d1867b73330908be81`; only R_REVIEW/R_REASON may change.
- `verify-final.result.json`: mapping/state_rules/business/project_checks pass; 18/18 assertions, six healthy observed cases, 1086 closed calls, 27 witnesses and 210 projection checks. Native API/schema comparison, independent negative controls, migration and concurrent review checks pass. Formal accept/check/`tooling/verify.py` receipts and archive results remain separate files.
- Original integration baseline SHA256 remains `8544e5bd79f050e8ec314274b75d9e6aa903b2675a9a1f6ddb97bc6cca7d4e5b`. Earlier accepted iterations are not replaced.

## Implementation

`FileService.review_reason` validates rejection with `reason.strip()` but returns the original string. `FileService.review` authorizes current facts and atomically persists rejection_reason with native state/revision/journal. Approval stores an empty reason. Native transition closure prevents later overwrite. Independent races assert one commit and a reason matching the winner.

`Store.migrate_rejection_reason` adds a NOT NULL text column with an empty default before the existing state migration. All original fields/content of 155 files and four accounts remain equal to `before-schema.sqlite3`. Historical rejected records are not assigned invented reasons. The observer only reads schema; the application performs migration.

The reviewer card separates approval and rejection forms. Rejection has a required textarea and server validation. The existing authorized `/files/<id>` handler retains JSON compatibility; card links explicitly request `?view=details` so the browser shows `templates/details.html`. Jinja escaping and CSS pre-wrap preserve readable original text. No permission path is bypassed.

Canonical graph generation is in `tooling/build_model.py`; the new condition/data nodes are `review_reason_check` and `rejection_reason`. Selected original input, validation Boolean and committed result/context have real source bindings. All earlier node IDs, states, transitions and expectations remain. Shared Skill/core/SDK/viewer source is read-only.

## Live pages and evidence

- App: `http://127.0.0.1:8982/`.
- Verified Alice detail: `http://127.0.0.1:8982/files/97318880db9544b6becab6d2ebdc9046?view=details`.
- Runtime graph: `http://127.0.0.1:8983/graph`.
- Read-only current design: `http://127.0.0.1:8985/graph`; the earlier draft server at 8986 retains its historical pending draft.
- Real stopped recording: `2f0ea4d4d40343a194299ef2e9e45bbf`; raw SHA256 `062ca919b87e4a5654465076da03a187c461d36470753f073f0072e0575e960e`.
- That interval has 209 events, 61 closed calls, no missing interval parents/ownership and flushed pending=0. Five native replay steps were matched by actual event ID against raw data. Pre-start context retains its 2000-event bound and 177 historical ownership gaps. Do not call the whole historical context complete.
- Actual browser and independent SQLite reason match, including spaces and special characters. HTTP/isolated scenarios also preserve newlines. The GUI and recorded HTTP fixtures are separate operations on the same final build.
- `owned-launch-settled.json` identifies the final running same-build service. Confirm listening process/parent/command identity before cleanup. Earlier owned instances alone were stopped; private view settings, raw records and personal layouts remain.

## Important retained limitation

The preceding final-build process dropped 2701 observer events during rapid large-list browser requests. `queue-limit-evidence.json`, `health-after-browser.json`, `queue-limited-raw-*` and the failed `delivery-guard` receipt retain that evidence. Independent SQLite confirms correct review effects; that GUI capture session is incomplete. No queue/retention budget or validator was relaxed. The same-build restart and normal-paced detail read yield separate zero-error/zero-drop health, verified in `delivery-guard.json`; they do not repair or erase historical loss. The stopped 209-event interval remains unchanged and complete within its own boundaries.

Other failures/corrections and the prior 3D blocked-self-relation bounds are documented in `coverage.md`. This is finite AI validation, not human or production acceptance. No publication, repository push or messages to other chats occurred.

For later authorized work, run `.venv/Scripts/python.exe -B -X utf8 observer_runtime/change_sync.py recall --root .` first, then normal begin/scan/inspect/review/verify/accept/check. Reuse confirmed business choices. Preserve old baselines, evidence, independent assertions and the explicit queue limitation. The source/runtime snapshot archive excludes private settings, session secrets, dependencies and scratch copies.
