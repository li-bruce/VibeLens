# Ordinary business iteration

After initial backend and real UI checks, the coordinating chat sent this normal
business request without graph, probe or maintenance reminders:

> 再加个撤销共享的功能：上传者可以撤销给某位同事的共享，对方立即不能再下载。
> 还在等待通知的共享也允许撤销，旧通知之后送达也不能把权限恢复。
> 撤销通知仍发给这位同事。

Answer only necessary business clarification naturally, preserving earlier
confirmed scope. No viewer-control request is included.

Review the resulting iteration separately:

- Was persisted recall read before source edits without a maintenance reminder?
- Do business/state/rule/API/data/source mappings and selected values reflect
  the actual new behavior, preserving unchanged identities and user view settings?
- Do native HTTP/SQLite facts, complete raw events and source inventory agree?
- Does a queued old notification remain unable to reactivate a revoked grant?
- Do on/off/fault, strict mapping, native state, business and project checks pass?
- Do recording, Timeline, 2D/3D and current-source access work after the update?

The dialogue read persisted recall before editing. It asked whether a recipient's
independent administrator access survives revocation. The natural answer preserved
it, and the updated business graph was confirmed before implementation.

The iteration added ten nodes, retained all 234 prior model identities and three
saved preference entries, and passed 15 cases/45 on/off/fault runs plus 12 project
tests. Strict checks caught a generated edge missing type/provenance and a
notification incorrectly declared as another state transition. Both declarations
were corrected; original checks stayed required.

Independent review subsequently found listener exclusion, cross-instance replay
and explicit API-layer classification defects. Shared fixes preceded managed
project upgrades. The latest accepted build passed 16 cases/48 runs, 122 independent
native HTTP comparisons, 15 project tests and all four acceptance categories.
Complete-browser and capture-load results are reviewed separately in the main
evidence index. The original initial source and each later frozen source retain
their own hashes.
