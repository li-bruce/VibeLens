# Preference acknowledgment follow-up

Both complete Chrome cases passed after replacing asynchronous `waitForFunction` preference checks: [names](names/result.json) and [viewer controls](viewer-retest/result.json). All original interaction and reload assertions remain.

The shared `tools/browser-preferences.mjs` helper subscribes to successful preference responses before reading the current server document. This covers already-saved settings and writes that finish while the read is in progress. Callers match the actual changed fields and require a newer revision when an action creates a new setting. The names test checks the naming mode; viewer dismissal checks both the focus revision and its inactive state.

[Five focused helper checks](helper-checks.json) cover an existing acknowledgment, a response arriving before a stale read, strict revision advancement, conversation scope and rejection of asynchronous matchers. No arbitrary delays or timeout increases were added.

The first viewer run failed before starting Chrome because Windows rejected port52972. Its [result](viewer/result.json) and [server log](viewer/server.log) remain. The unchanged fixture passed on port18878. This environment failure is not counted as a passing test.

[Summary and tested source hashes](summary.json). The separate [code browser checks](../code-browser-ack/) cover the other three affected sites.
