# Frontend HTTP response repair

## Authorized boundary

Continue the source-only archive described in `continuation-origin.json`. Preserve
project/node identities, confirmed business requirements, the native state engine,
and every byte under `.stategraph/initial-v1`. Only this isolated project is changed.
The maintained Skill and the original trial/processes remain untouched.

## Failure and repair

`http-entry-before.json` reproduces the missing response: a real form upload returns
HTTP 303 while `api_command` returns empty outputs. The upstream Flask exclusion
previously admitted only `/api/`; manual form/detail spans ended before the framework
finalized the response.

The integration now selects the upstream Flask request by native method/route.
The same upstream span owns its SDK identity, request lifetime, framework status
and exception class. Form and detail handlers no longer create duplicate request
spans. The business spans, permissions, transactions and native state engine retain
their existing execution boundaries. `api_workspace` maps the page loader to
`create_app.index`; the business node remains `workspace`.

## Independent readers and retained protection

`tests/http_cases.py` reads Flask's native route table, selected route arguments,
the native SDK SpanContext before teardown, and the actual WSGI `start_response`
status. It never reads expected values from observer events. Native and observed
requests join by their trace/span pair, not arrival order. Runtime mapping checks
compare every HTTP status and selected input; protected mapping cases/context
identities and whitebox field assertions retain these obligations. The canonical
context-field protocol accepts trace/provenance/exception metadata, so ordinary
HTTP statuses use the existing top-level native `mapping_checks` mechanism.

The three frontend cases cover actual login/upload/review/share/logout forms,
workspace pages, file information, downloads, waiting and delivery activation,
redirects, rejection, missing files, unauthenticated access, origin/CSRF denial and
real Flask 500 responses. The original eight scenarios remain in on/off/fault modes.
Source routes are independently extracted and compared to native routes, handlers
and API nodes. Static, observer and export requests are checked for no new events
and unchanged business storage. In-memory negative copies remove/corrupt a response;
they never replace recorded evidence or accepted credentials.

## Retained development failures

- The isolated source archive intentionally had no JavaScript dependencies. The
  first recall reported the missing parser. Locked dependencies were installed
  only into this project; no scanner or validator was patched.
- The first model refresh found no runtime SQLite database, as expected for a
  source-only continuation. Native initialization created fresh synthetic data.
- `http-bootstrap-observations.stderr.log` retains a native-reader failure on a
  missing file: the reader indexed an empty result before native handling returned
  404. The reader now preserves absence and leaves the application response intact.
- `http-denials-retest.json` and its logs retain the focused clean retest.

## Acceptance status

`review/http-entry-attempt-01/` retains the clean managed scan, inspect, verify,
accept and check sequence. Mapping, state rules, business and project checks all
passed. The runtime matrix contains 33 runs, including 45 native HTTP responses
in the enabled frontend cases. All enabled runs report zero capture/data errors,
zero drops and zero open automatic spans. Eight project tests passed, including
recording with a real 303 form response, queued stop, focused values, exclusion,
old-build queue handling and three isolated response negative controls.

`continuation-integrity.json` confirms every original `initial-v1` file is unchanged,
138 copied canonical runtime files match the source archive, and the native domain,
storage, permissions, state engine and launcher Python sources remain unchanged.
`http-acceptance-summary.json` identifies the accepted candidate and build.

Browser acceptance is owned by the parent conversation; this continuation does
not run browser tools or claim an independent browser pass. Service URLs and the
build-identity check are recorded separately in `http-service-handoff.json`.
