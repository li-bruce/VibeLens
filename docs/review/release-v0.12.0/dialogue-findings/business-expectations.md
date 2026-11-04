# File-sharing trial expectations

Status: planned independent checks, not execution results. The coordinating AI
provided the natural-language answers under the user's authorization. These
expectations come from those answers, independently of the generated graph.

## Confirmed behavior

| Operation | Independent expectation | Evidence to compare |
| --- | --- | --- |
| Login | Valid local credentials establish the user's identity; invalid credentials do not | Actual response, session identity, observed request completion |
| Upload | A new file waits for review | Stored file identity, uploader, initial review state, actual transition witness |
| Review | A reviewer may approve or reject another person's file | Actual actor and owner, guard inputs, previous/next review state |
| Self-review | A reviewer cannot review their own upload | Denied response and unchanged file record; captured denial is still observed |
| Rejected upload | Uploading again creates a new file; the rejected record remains | Two distinct identities and preserved old decision |
| Share | Only the uploader shares an approved file with a specified local account | Native approval read, owner check, grant and notification writes |
| Invalid share | Unapproved file or another uploader's file is refused | Response, unchanged grants/messages, actual rule evaluation |
| Receive | The selected recipient sees a message and can download | Message recipient, active grant, returned file bytes |
| Other recipient | A different account holding the URL cannot download | Actual denied request, no bytes, captured completion and evaluated inputs |
| Revoke | Only the uploader can revoke their own issued grant | Actual owner check and grant change; review state unchanged |
| Download after revoke | A new request through the old URL is refused | Native grant read at the request boundary, response and observed value |
| Transfer already started | Revocation does not have to interrupt a transfer already running | If exercised: controlled overlap and bytes; otherwise report unrun |

V1 has one recipient per file. A later natural-language iteration will explicitly
request multiple recipients before its expectations are added. No expectation
below silently changes the approved V1 behavior.

## Observation and maintenance checks

- Compare source-free confirmation with the bound business, review-state and
  shared-rule definitions. Keep the three-model rejection as a separate result.
- Compare actual framework responses, direct database reads, native transition
  records, policy inputs/outputs and selected values with their graph events.
- Confirm denial/error paths close their real invocation lifetimes and retain
  the correct execution, actor, object and cause references.
- Use concurrent users and the application's actual notification mechanism to
  check isolation and causal links. Do not infer causality from timing alone.
- Run the same business cases with observation on, off and failing. Observer
  traffic must not create application events or change business outcomes.
- After a confirmed business iteration and a source-only refactor, require the
  normal recall/scan/inspect/verify/accept/check workflow, preserved protected
  expectations, current source bindings and real runtime evidence.
- Remove one required witness or alter one association in an isolated negative
  fixture. The existing checker must reject it. Keep the failed input and report.

Report concept binding, mapping/observation, business behavior and Web interactions
separately. A passing finite case is not evidence for every possible execution.
