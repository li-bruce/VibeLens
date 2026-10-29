# Development cost separation

Business scope was fixed by simulated answer U2. No business requirements were added during framework upgrades or final acceptance repair.

| Work category | Actual record | Accounting boundary |
| --- | --- | --- |
| Initial business implementation | Login, upload, owner-only sharing, metadata and exact download | Initial requested scope only |
| Initial framework installation | One normal bo_upgrade apply | Initial integration, not a new business feature; duration not measured |
| Additional framework updates | 4 normal bo_upgrade applies; all commands succeeded | Separate environment work |
| Measured additional upgrade CLI time | 9.053 seconds | Command wall time only; excludes analysis, integration repair and rechecks |
| Full verification entrypoint executions | 10 actual invocations, including failed/stale and repeated rounds | Separate validation work; not business additions |
| Framework integration repairs | Narrow project-schema enum adapter, projection-order composition, explicit layout alias | Separate integration/debugging work |
| Delivery/test repairs | Temporary path/connection cleanup, safe capture summary shape, locator readiness and Windows process-tree cleanup | Delivery and verification work |

Per-run active effort was not fully timed and is left unknown, not estimated or billed as business work. development-costs.json records the actual verification sequence and measured command durations. framework-upgrade*.json retain exact command outputs, changed files, retirements and conflicts. The canonical freeze instruction is preserved in framework-freeze-instruction.txt. The original baseline was never recreated.
