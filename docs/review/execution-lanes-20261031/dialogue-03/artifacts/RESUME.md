# Resume This Prepared Project in a New Conversation

Current disposition: frozen preparation. The graph rules are confirmed by U002;
business and runtime-mapping acceptance have not passed. Integration, application
execution and iteration were expressly stopped in the preparing conversation.

Read these records before proposing or making changes:

1. `review/FROZEN.md`, `review/freeze-verification.json`, `review/freeze-manifest.json`.
2. Exact scenario messages in `review/user-request-001.txt` and
   `review/user-confirmation-002.txt`; the business user is the coordinating AI.
3. `discovery.json` for confirmed flow, permissions, source provenance and the
   D_GRAPH_CONFIRM resolution history; `intent.json` for stable requirement IDs.
4. `bo_stategraph/project.json` and `review/state-declaration.json` for the reused
   native machine; `review/reuse-manifest.json` for reuse/exclusion boundaries.
5. `review/failure-fix-retest.md`, `review/viewer-observation.md`, installation logs,
   design screenshot and historical design verification reports.
6. `AGENTS.md`, `sync.json`, `mapping.json`, `whitebox.json`, `acceptance.json` and
   unchanged independent checks under `tooling/`.

Preserve the existing rules: upload assigns exactly one other existing account
as reviewer; only that reviewer reviews; rejection ends the flow without
resubmission; only the uploader shares an approved file with one recipient;
recipients cannot forward. Reading means metadata/download and always requires
login. Uploader/reviewer can read throughout; recipients need approval and an
actual share to their account; all other accounts are denied. Use fixed test
accounts, Python, SQLite and declaration-driven execution.

Do not replay historical observations as fresh evidence, import old acceptance
or reset protected expectations. The prepared application/graph ports are
8982/8983 and the future database path is `var/team-files.sqlite3`; no application
database or new runtime integration exists. The graph service is stopped.

The preparing conversation explicitly invoked the requested local VibeLens Skill.
That activation does not silently activate a new conversation. A new continuation
request must provide its own authority and, when using VibeLens, explicit Skill
activation. Shared source, other projects and installed managed files remain
read-only; publishing and example-local framework workarounds remain prohibited.
Record and verify a later authorized shared-viewer upgrade separately.
