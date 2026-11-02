# Standard HTTP control-route repair

Trial 09 upgraded normally, then the standard service returned HTTP 404 for
`/api/vibelens/control/context`. The previous HTTP regression exercised `BOWeb`
through a fixture server. It did not exercise the standard server's separate GET
whitelist, so component/browser passes and complete gate 09 did not establish
that this entrypoint worked. The application trial correctly stopped before
acceptance. Preserve this as a maintenance integration defect.

`control-route-negative-01.log` reproduces the 404 through the actual shared
`make_server(GraphSession(...))`. The new test uses its real HTTP dispatcher,
normal control CLI and project scope. It also checks that this endpoint does not
read history, that queued plans retain the actual build, that foreign origins
remain denied, and that disabling Web hides the endpoint while health stays
available. HTTP controls add no observations.

The repaired dispatcher delegates shared GET routes to `BOWeb.get`, matching the
existing shared POST dispatch, instead of maintaining a second endpoint list.
`control-route-retest-01.log` passes all ten capture/session/HTTP tests. Existing
large-payload and control tests remain unchanged. Both examples are verified and
frozen in `control-route-20261101-verification.json`; source gate 14 passes for
121 Python and 90 JavaScript modules. Complete repository run 10 passes from
03:24:06 to 03:31:58 local time. Trial 10 continues the affected application
controls and ordinary business iterations after these shared gates.
