# Display metadata and event ingestion

The Node trial's real browser recording reported transport timeouts and an
incomplete queue drain. These failures remain distinct from earlier application
startup connection failures. A separate deterministic framework check found that
the live view held the event-admission lock while reading semantic names and
recorded verification details.

`display-lock-first.log` reproduces both lock dependencies: an actual HTTP event
cannot finish until the delayed display reader is released. The fix reads those
presentation artifacts after releasing the lock. Runtime state, retained event
references, sequence and binding status are still captured together. Source
validation, producer deadlines, event validation and recording completion rules
are unchanged.

`display-lock-retest.log` and `focused.log` retain the follow-up checks. The latter
runs 47 tests, including event delivery while display IO remains blocked, the
view's original runtime boundary, source-request concurrency, API projections and
semantic-name validation. Source formatting and lint also pass.

This establishes a framework concurrency defect and its repair. It does not by
itself prove the cause of every timeout in the Node application. The independent
trial must compare the same real recording with fresh installations, retaining
its request timing, producer health and original interrupted records. The
component-tested installation is explicitly diagnostic until full regression
and native retesting complete.

The full runner passed 95 unittest suites (1,108 reported test records, one
Windows file-symlink privilege skip), including the enabled pinned TLC checks.
Both managed examples passed verify, accept and check with unchanged business
source; their accepted rounds are frozen. The diagnostic Node recording still
had queue backlog and timeouts, retained in its trial directory. This repair is
therefore a verified component correction, not complete P7 acceptance.
