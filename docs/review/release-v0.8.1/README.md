# v0.8.1 validation repair

The main v0.8.0 build passed all seven jobs. Its parallel feature-branch run failed once in the Windows/Python 3.11 test reader while the watcher atomically replaced `maintenance.json`.

- [Original failure](windows-watcher-first.log): GitHub run [40251105988](https://github.com/li-bruce/VibeLens/actions/runs/40251105988), job 121342972763.
- Repair: wait for the actual watcher JSON, retrying temporary sharing denial or file absence within the original **8-second** deadline. Predicate checks, business assertions and polling interval are retained. Invalid JSON still raises immediately; permanent denial still fails.
- Added injected transient/permanent-denial and invalid-content regressions, alongside the actual watcher registration/acceptance test. [Local retest](watcher-retest.log).
- [Source quality](source-quality.json) remains separate from the full repository checks. [v0.8.0 acceptance](../release-v0.8.0/README.md) documents the unchanged engine, source mapping, database, browser and package checks.
- The 222-file Skill subtree and release ZIP are byte-identical to v0.8.0. This patch changes repository validation and the displayed release link; it keeps existing runtime approvals valid.

This is a test observation repair. It does not substitute a successful result for unreadable content or weaken the expected graph updates.
