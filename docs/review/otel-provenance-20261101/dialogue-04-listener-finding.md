# Application and observer listener identity

Independent native requests reproduced a second exclusion problem after the
ordinary business iteration had passed its selected cases:

| Actual request to application port 50949 | Native response | Recorded events |
| --- | --- | --- |
| `/api/events` | 404, `route_not_found` | 0 |
| `/api/unknown-native-operation` | 404, `route_not_found` | 2 |

[Original native evidence](dialogue-04-exclusion-reproduction/result.json)
retains supplied W3C IDs, actual responses and matching raw events. The first
request executes the application's registered API dispatcher. Its name resembles
an observer endpoint, but the real observer is on port 50950.

The integration excluded guessed observer path names on the application
listener. That classification can also hide an application's real events,
recordings or reporting features. Exclusion must follow the actual service and
registered endpoint, not the path's vocabulary.

The shared Skill guide now states that distinction. Its real SDK regression
captures application `/api/events` while excluding an actually registered
observer UI; all 30 SDK tests pass. The ordinary accepted source is frozen in
`dialogue-04-v2-pre-exclusion-fix-source.zip`. The isolated dialogue is applying
the integration repair in a separate managed change, retaining every previous
baseline and checking the actual observer listener for zero application events.
