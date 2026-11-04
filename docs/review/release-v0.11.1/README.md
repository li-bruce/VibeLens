# v0.11.1 patch review

Published: [v0.11.1](https://github.com/li-bruce/VibeLens/releases/tag/v0.11.1),
commit `7cc0bce908efdac25f70c6d4439a5210b235ad7c`.
The [exact candidate's eight CI jobs](../graph-quality-20261104/publication/ci-candidate-7cc0bce9-final.json)
all passed. [Public release and Pages verification](../graph-quality-20261104/publication/public-v0.11.1-01.json)
checks the tag, deployed commit and frozen archive digest.
The [official tag installation](../graph-quality-20261104/trial-audit/release-install-parity.json)
matches all 305 candidate Skill files used for the independent iteration.

The [graph-quality review](../graph-quality-20261104/README.md) retains the initial
v0.11.0 local acceptance, publication, remote failures and subsequent repairs.

This patch addresses observed equal-clock concurrency, legacy data lifecycle
presentation, CI portability and explicit first-party source boundaries.
The [local candidate gate](candidate-gate.json) passed full repository verification,
source quality, scope regressions, real-browser checks, both managed examples and
an isolated Git export. The [independent audit](../graph-quality-20261104/publication/candidate-independent-audit.md)
matches every ZIP entry and the protected cores to frozen Git content. Remote CI,
publication and the fresh GitHub-installed observer upgrade have separate receipts.

The independent chat installed v0.11.0 from GitHub and completed its first
application: login, private upload, sharing, download and revocation. The
[first-phase audit](../graph-quality-20261104/trial-audit/v1-completion-audit.md)
records business, mapping and actual HTTP evidence separately. A second dialogue
confirmed a private sharing-note iteration. The coordinating test installed the
frozen candidate directly from GitHub commit `c56fd19f` and checked all 305 files;
the managed runtime upgrade and iteration are now in progress. Official release
tag parity subsequently passed without replacing or modifying the active copy.

The first candidate CI run found one remaining test-launch assumption: the
caption browser fixture required a local `.venv`, while GitHub provides Python
on `PATH`. The test now follows the existing interpreter-selection convention
and reports startup errors normally. Its original four checks pass in Chrome
both with a local venv and without one. The
[failure log](../graph-quality-20261104/publication/ci-browser-c508fdc7.log) and
[focused retests](../graph-quality-20261104/publication/caption-ci-portability.json)
are retained. This test-only repair leaves the frozen Skill archive unchanged.

The next CI run reached the live lifecycle test and reproduced a recording-start
race: a click returned before the asynchronous recording request completed.
The pre-span fixture therefore started business work outside its own recording
boundary. The test now waits for the actual start acknowledgment and active
controls before work, and for painted causal links before reading geometry.
The original flow, duration and clipping assertions remain required. Default,
registered and deliberately mid-span Chrome retests passed; the
[CI failure](../graph-quality-20261104/publication/ci-candidate-c56fd19f-browser-failure.json)
is retained. No application event or lifecycle was fabricated.

The concurrent-worker fixture had the same start barrier problem and a stale
formal-parameter mapping. It replaced `advance(state, ...)` with a function
whose `state` was local, while retaining the original parameter reference.
Strict source validation correctly rejected it. Restoring the actual initial
state argument makes the mapping accurate; both concurrent Chrome variants
now pass their original two-group, layer-row, event-count and dependency-curve
assertions. The runtime validator and native state engine were unchanged.
