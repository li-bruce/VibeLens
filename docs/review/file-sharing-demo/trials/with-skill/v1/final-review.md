# Initial version acceptance

Completed on 2026-10-29T07:46:05.503950+08:00. This is an independent local implementation using supplied simulated answers, not independent human testing.

- Application build: `fa390db0b5dec9e1cfcaabc91fa45ef574b738b1ceb6eeba29c13eeaaed7552e`
- Accepted source/tool candidate: `739a82501fe7cc9e53b026d0a53c7f41bff7a3e97b27a078c76d3510d27add42`
- Application: http://127.0.0.1:8850/
- Graph: http://127.0.0.1:8847/graph

| Check category | Final result | Evidence |
| --- | --- | --- |
| Implementation mapping | Passed | change-verify.json; post-browser-change-check.json |
| Native state constraints | Passed | runtime-observations.json; evidence-checks.json |
| Business rules | Passed, 39/39 assertions | change-verify.json |
| Application checks | Passed, 12 tests | .stategraph/initial-v1/checks/test-0.json |
| Evidence/protocol checks | Passed, 8 checks | evidence-checks.json |
| Architecture | Passed | architecture-check.json |
| Headless browser | Passed, 11 steps and 5 screenshots | browser/report.json |
| Recording/replay | Passed, 552 events, no gaps | browser/recording-stop.json; initial-v1/recording.json |
| Current native policy copies | Passed, five exact managed/canonical modules | framework-parity.json |
| Original baseline | Unchanged | framework-parity.json |
| Current source/tool acceptance | Passed; no pending upgrade files | post-browser-change-check.json; final-framework-upgrade-plan.json |

Outstanding failed checks: none. Historical failures remain in failure-fix-retest.md and preserved records. Human usability, production deployment and optional 3D interactions were not exercised.

The final CLI-only formatting synchronization changed the tool candidate, while all bound application source bytes and the browser-tested application build remained unchanged. The final headless screenshots and recording therefore retain the exact final application build identity. The final managed tool copies are separately checked against the frozen canonical Skill.

The original 342-event recording and layout migration failure are preserved in preserved-342-event-run/. The 482-event run is preserved in superseded-fa390db0b5de/. Layout settings were migrated through the declared alias, with before/after files retained. The accepted initial graph and machine are frozen in initial-v1/ for the later iteration comparison.

No revocation or deletion feature is implemented. Version one stops here and waits for the next instruction.
