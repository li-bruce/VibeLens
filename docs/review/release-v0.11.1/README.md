# v0.11.1 patch review

The [graph-quality review](../graph-quality-20261104/README.md) retains the initial
v0.11.0 local acceptance, publication, remote failures and subsequent repairs.

This patch addresses observed equal-clock concurrency, legacy data lifecycle
presentation, CI portability and explicit first-party source boundaries.
The [local candidate gate](candidate-gate.json) passed full repository verification,
source quality, scope regressions, real-browser checks, both managed examples and
an isolated Git export. The [independent audit](../graph-quality-20261104/publication/candidate-independent-audit.md)
matches every ZIP entry and the protected cores to frozen Git content. Remote CI,
publication and the fresh GitHub-installed observer upgrade remain separate checks.

The independent chat installed v0.11.0 from GitHub and completed its first
application: login, private upload, sharing, download and revocation. The
[first-phase audit](../graph-quality-20261104/trial-audit/v1-completion-audit.md)
records business, mapping and actual HTTP evidence separately. A second dialogue
confirmed a private sharing-note iteration and paused implementation for the
official v0.11.1 upgrade. That upgrade and iteration remain pending.

The first candidate CI run found one remaining test-launch assumption: the
caption browser fixture required a local `.venv`, while GitHub provides Python
on `PATH`. The test now follows the existing interpreter-selection convention
and reports startup errors normally. Its original four checks pass in Chrome
both with a local venv and without one. The
[failure log](../graph-quality-20261104/publication/ci-browser-c508fdc7.log) and
[focused retests](../graph-quality-20261104/publication/caption-ci-portability.json)
are retained. This test-only repair leaves the frozen Skill archive unchanged.
