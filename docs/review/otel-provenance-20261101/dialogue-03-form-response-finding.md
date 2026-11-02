# Browser command response coverage

The independent browser uploaded an actual file through its file input, approved
it through the review form, waited for notification-dependent activation, shared
it, and downloaded identical bytes as the recipient. The business flow passed;
this does not establish complete HTTP observation.

Evidence: `independent-browser-02/flow-result.json` and `flow-events.json`.
The browser observed HTTP 303 on `/command/review` and `/command/share`.
Their source-bound `api_command` spans have enter/return pairs, but their return
events contain empty outputs. The actual framework response status is absent.
The existing `/api/` requests do capture actual HTTP status.

The trial's upstream Flask instrumentation explicitly excludes every route
outside `/api/`. Its manual form-handler span closes before the framework
response and does not capture that response. The earlier backend acceptance
covered API scenarios, so it did not expose this frontend-route gap.

The shared Skill now derives HTTP cases from native routes and actual frontend
actions, including HTML commands and redirects. A real upstream Flask regression
covers command responses 303, 403 and 500 plus observer-route exclusion. This is
an integration/guidance coverage repair; no business rule or native state-machine
behavior should change. Trial correction and complete revalidation remain pending.

The preceding browser-flow failure is retained in `independent-browser-01` and
`independent-browser-flow-01.log`. Its locator incorrectly searched a file card
for a button in the separate review panel. That failure belongs to the test
script, not the application. The corrected locator passes in attempt 02.
