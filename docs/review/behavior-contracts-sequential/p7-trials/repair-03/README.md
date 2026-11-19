# Node HTTP observation boundary

This repair remains part of P7, not final acceptance of the two trial projects.

## Actual application diagnostic

`native-origin-result.json` and `native-origin-events.json` preserve an independent
check of the in-progress Node observe application. Actual HTTP statuses were
403, 400 and 401; only 400 and 401 had corresponding API returns. Source hashes
before and after are identical. `native-origin-check.mjs` uses the native
application, its real SQLite store and its actual observation adapter; it does
not manufacture business events.

The origin guard ran before the application's route observation hook. A probe
inside the route could not see that rejection. This is a general integration
placement issue, so the maintained adapter and Skill are repaired before asking
the isolated trial to adopt the new package.

## Shared repair

`bo_http.mjs` wraps a native Node request listener, including an Express app. The
project supplies the existing route-to-source identity resolver. Unknown or
observer requests return `null` and remain outside the selected observation.
No routing, permission, request body or business transition is implemented here.

The adapter closes its physical scope at `ServerResponse.finish` or `close`.
It records only declared fields: actual sent status, completion and duration.
A disconnect before headers has no fabricated status. Completion is transport
progress, not a business outcome or proof that the client received the response.
See [Node's HTTP response events](https://nodejs.org/api/http.html#class-httpserverresponse).

`BOProbe.runUntilEnd` adds an explicit callback lifetime while retaining native
return values and escaping exceptions. Node task-local context is initialized by
this Node-only adapter; an existing OTel provider/context manager takes precedence.
An ordinary asynchronous child and a point value retain their request parent.

## Regression history

- `http-boundary-first.log` / `http-boundary-diagnostic.log`: the new wrapper's
  native-context check failed because no task-local store had been installed.
  The adapter now initializes the existing native store itself. The original
  OTel trace and state implementations remain unchanged.
- `http-boundary-retest.log` / `http-boundary-final.log`: actual early guard/parser
  exits, concurrent 201 responses, excluded request, premature disconnect, and
  native exception identity pass with native and OTel contexts. Disabled and
  failed transport produce the same native status/body and operation counts.
- `integration-first.log`: the old installation test expected two native files.
  The repaired test requires the exact three-file inventory and imports the new
  HTTP helper without Python or viewer dependencies. `integration-retest.log`
  passes all ten checks.
- `telemetry-node.log`: existing SDK identity, detached tasks, propagation and
  linked-job regressions still pass.
- `full-verify-first.log`: the package link gate rejected local-path placeholders
  in two derived dialogue Markdown files. The exporter now renders every declared
  path alias as text, while retaining working public/relative links. The original
  Markdown is saved as `*-dialogue-render-before.txt`; public JSON and source
  fingerprints are unchanged (`dialogue-render-repair.json`). The existing
  WORKSPACE and new custom-alias/privacy cases both pass, followed by the unchanged
  package gate (`dialogue-export-retest.log`, `package-retest.log`).

The fresh trial must still adopt the package, reproduce the previously missing
response, and complete its source/runtime/browser and iteration checks. A passing
adapter test does not substitute for that application evidence.
