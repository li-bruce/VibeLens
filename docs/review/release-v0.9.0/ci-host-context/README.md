# Isolated host context in the HTTP test

The earlier shared-policy workflow failed all four OS/Python test jobs at `tests/test_runtime_http.py`: its control-activation subprocess inherited `CODEX_THREAD_ID` from the developer shell. GitHub runners have no Codex host conversation. The runtime correctly rejected activation; this was a test-fixture environment dependency.

The HTTP fixture now supplies `runtime-http-test` only to its simulated control subprocess. Production activation is unchanged. An additional controller negative removes the host identity, requires rejection and checks that no new scope directory is written. All previous assertions remain.

The local retest ran the controller and complete live HTTP test with `CODEX_THREAD_ID` removed from their outer environment. Both passed: 18 controller tests and the original real runtime/SQLite/observer-isolation test. The original public CI log and local no-host retest are retained beside this file. The Skill payload and archive are unchanged.

[Original decoded cloud log](github-before.zip) · [hash and run](github-before.json) · [no-host retest](no-host-regression.zip).
