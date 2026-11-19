# Early HTTP response capture

This independent framework check extends the native trial review. It is not a
claim that the in-progress trial applications have completed mapping acceptance.

## Reproduction

A real Flask application registers an origin/auth-style guard before installing
the pinned upstream OpenTelemetry instrumentor. Three requests actually return
403 (guard rejection), 400 (JSON parsing), and 201 (handler completion). The old
integration emits only the latter two return events. The upstream diagnostic is
`Flask environ's OpenTelemetry span missing at _start_response(403 FORBIDDEN)`.

The failure is retained in [the first run](http-boundary-regression.log). Request
statuses and entry into the native business operation are independently asserted;
an empty observation cannot satisfy the request case.

## Cause and repair

The upstream instrumentor appends its Flask request hook. Earlier application
hooks can return before span creation. Matching or closing spans in the VibeLens
processor cannot recover a span that never existed.

The managed Python adapter now supplies `bo_instrument_flask`. During application
construction it installs the upstream instrumentation and promotes only its new
request hook ahead of native guards. Their relative order, authorization and
responses stay unchanged. It rejects a second installation instead of replacing
an application-owned provider. The original SDK, registration protocol and state
executors remain in use.

Skill guidance now explicitly covers early authentication, origin, CSRF and
parser exits for every HTTP integration. Express integrations similarly place
their actual request boundary ahead of rejecting middleware or initialize HTTP
instrumentation before loading the application. Route-only capture is insufficient.

## Evidence

- [Focused repaired run](http-boundary-retest.log): actual 403/400/201 returns,
  distinct invocation identities, closed spans and unchanged native operation.
- [Telemetry regression](http-boundary-suite.log): first 31-test run passed;
  the subsequent full runner also includes the duplicate-installation regression.
- [Repair round](repair-02/): managed regeneration, full checks and later receipt.

The helper does not solve arbitrary framework dispatch, sample every input, or
invent missing business executions. Application acceptance still requires cases
at its real boundaries with source-bound registrations and independent outcomes.
