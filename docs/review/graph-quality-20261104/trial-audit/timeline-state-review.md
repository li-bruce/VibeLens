# State occupancy in the independent dialogue recording

The reviewed image is the trial's retained `review/browser/graph-replay-last.png`.
The matching immutable recording contains 340 events and three runtime frames.
The [interval extraction](timeline-state-intervals.json) has one file instance,
one execution lane and one state subtrack. Installed and canonical timeline
indexers produce the same result.

| State | Start (ms) | End (ms) | Meaning |
| --- | ---: | ---: | --- |
| stored | 6829.166 | 7196.328 | The uploaded file has no active share |
| shared | 7196.328 | 8933.370 | The file is shared |
| revoked | 8933.370 | 10637.052 | The final observed state continues to the recording boundary |

No pair of these intervals overlaps. The last interval has no observed next
state, so `duration: null` and `unfinished: true` are appropriate occupancy
metadata. A persistent state is distinct from a running function; ending the
recording does not imply ending that state.

The apparent continuous purple strip comes from adjacent occupancy segments using
the same layer color. The first segment is narrow at this zoom, leaving no caption
space. The shared segment's label and duration badge occupy separate clipped
regions, followed by the revoked segment's separately clipped caption. Causal
stems cross the state row and add visual density. Source inspection found no
proven interval, object-scope or text-clipping defect in this retained sample.

Possible later visual refinements are subtle separators at state boundaries and
measured caption allocation with hover access for narrow segments. They should
preserve exact times, state persistence and object grouping. This review made no
timeline product changes or requests to the trial application. The original trial
browser evidence covers replay selection and scrubbing; it does not establish
3D or custom-view acceptance.
