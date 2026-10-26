# Afterlight — a recorded VibeLens debugging case

A browser frontend and Python backend store versioned images, review messages and an exhibition in SQLite. The case follows an old preview that accidentally publishes a replacement image, then a small policy change and the same operation repeated successfully.

[Explore the recorded project in 2D and 3D](https://li-bruce.github.io/VibeLens/demo.html) · [中文说明](README.zh-CN.md) · [Scripted conversation](review/dialogue.md)

## Run

From the repository root, with Python 3.11+ and Node.js 20+:

```sh
python -m pip install -r examples/exhibition-review/requirements.txt
python tools/setup_adapters.py
python examples/exhibition-review/run.py --port 8894
```

Open [the application](http://127.0.0.1:8894/app) and [VibeLens](http://127.0.0.1:8894/graph). The launcher prints both URLs. It creates a fresh project under `.validation/afterlight-<timestamp>`; `--root PATH` selects another empty directory. Stop with Ctrl+C. The repaired version is the default.

Use a real PNG in the Artist panel. Open it in Reviewer, replace it in Artist, then approve the old preview. The repaired program returns `stale_review`. Open the latest version and approve it to publish. Start/stop recording in VibeLens around these actions; expand the approval node and inspect the policy values and queries.

## Replay the complete case

```sh
python -m unittest discover -s examples/exhibition-review -p test_domain.py
node tools/test_exhibition_case.mjs
python tools/build_site_viewer.py
node tools/test_case_browser.mjs
```

The browser tools require Playwright and Chromium (`npm install playwright`, then `npx playwright install chromium`), or the existing workspace runtime. Set `BO_BROWSER_EXECUTABLE` for an installed Chrome. `BO_CASE_EVIDENCE` selects a fresh output directory. The first browser tool executes v1 and v2 in separate project directories and exports the actual recordings to `docs/site/case-data`. The second serves Pages locally and tests its real embedded viewer. Regenerating fixtures is an explicit review action.

V1 is deliberately faulty: its policy omits the version comparison. Its business test must be red. V2 must reject the stale review, leave the exhibition unchanged, and publish after a fresh review. A successful test tool exit means this red/green teaching sequence behaved as expected; it does not mean the faulty v1 was correct.

## Source map

| File | Responsibility |
|---|---|
| `web/app.js`, `web/index.html` | Upload, open preview, approve, exhibition and messages |
| `app.py` | Native HTTP entrypoints and local launcher |
| `domain.py` | Application behavior, image check and version selection |
| `policy.py` | Repaired role and version comparison |
| `repository.py` | SQLAlchemy table declarations, queries and transactions |
| `bo_integration.py` | Optional VibeLens call/data capture and state snapshots |
| `prepare.py` | Source-bound declarations, data export and deliberately faulty v1 |
| `test_domain.py` | Independent expectations with observation absent |

The graph connects API, business, states, rules, functions/values, data operations, data structure and static source. It starts with the business flow. Local source detail is bounded; Code structure opens the full indexed scope. Static source links do not claim runtime execution.

## Evidence and limits

The Pages graph uses the maintained Pixi/Three.js viewer. A small read-only transport supplies captured JSON instead of running a backend on GitHub Pages. It preserves actual events, source identities, state frames and query evidence. Layout choices on Pages stay in that browser. New recordings are available in the locally running project.

The dialogue is simulated and the defect seeded; this is not an independent AI trial. Identities are fixed demo roles, with no login system. Image checking recognizes a PNG header, not every image format or a hardened decoder. SQLite is the executed store. The case does not add claims about other databases or large-graph performance. See [review material](../../docs/review/pages-case/README.md) for failures, repairs, retests and screenshots.
