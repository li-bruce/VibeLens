# Review-oracle correction

The retained `passed: false` result used the HTTP request's earlier session as
the expected actor at `sign_in.enter`. That is the wrong boundary for this app:
`app/web.py` clears the session before calling `sign_in`. The function's observed
anonymous principal therefore does not establish an actor-mapping defect.

The coordinating review caused this false positive. Its first follow-up also
led to an unconfirmed expectation that rejected reauthentication would retain
the previous login. That added expectation was withdrawn; original business
requirements and the initial protected baseline remain authoritative.

The original result and raw events are retained unchanged. The corrected helper
reads native session/user facts through a read-only wrapper at the actual domain
function entry. Request-entry identity remains separately visible. Final retest
evidence is indexed in the parent review after the candidate stops changing.
