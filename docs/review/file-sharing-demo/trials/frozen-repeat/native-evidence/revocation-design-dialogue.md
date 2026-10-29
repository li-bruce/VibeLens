# Revocation iteration: design dialogue

## Authorization and provenance

- Date: 2026-10-29 (Asia/Shanghai).
- Source: the forwarded current request in chat `01a18512-6617-7791-aa29-f2aeb9312859`; no source-chat inspection.
- Scope: owner cancels one file's sharing relation to a selected recipient. A download started after that commit must read current permissions even from an unchanged page. Other recipient relations and owner access remain. Sharing to that recipient again is allowed.
- Frozen canonical revision remains `e69ce0921ac06fb455ec0aedc403e24d74babebc`.
- The user explicitly permits simulated design answers, provided their simulated provenance is clear. No independent human acceptance is claimed.
- Confirmed requirement IDs for this change: `R_REVOKE`, `R_SHARE`, `R_ACCESS`, `R_BOUNDARY`, `R_STORAGE`, `R_GRAPH`.
- No blocking business ambiguity is present. The simulated persona restates the supplied scope only and adds no business feature.

## Original request

> 再加一个取消共享功能：我是文件所有者，可以取消给许宁的共享。许宁已经打开的旧页面，下一次下载也应当被拒绝；给其他接收者的共享，以及我自己的访问都保留。以后可以再次共享给许宁。先把变化后的业务图给我看一下，再按这个范围实现、同步图和采集，并完整复测。仍然用冻结版 e69ce09，不改框架的校验或测试。设计中的必要问题可以拟人化自行模拟我的回答，明确记录模拟来源，不扩展功能。另有一个框架回放的小问题正在独立处理：实际 Boolean 规则依赖的 data 事件与 guard 逻辑边匹配不完整，这不影响本轮业务实现和检查；这轮先保留现有框架，不自行修补它。

## Simulated scope restatement

Assistant understanding: 取消共享只移除“这份文件 → 许宁”这一条关系；旧页面下一次下载仍向服务端发请求，服务端重新查关系。周岚若是这份文件的另一个接收者，访问继续保留；林舟作为所有者也继续访问。以后再次共享给许宁即可恢复访问。

Simulated user persona answer, authored by the coding agent under the explicit permission above: 对，就按这个范围做，不需要额外功能。

This is a simulation of the already supplied scope, not a new human reply. The graph must be displayed before behavior implementation.

## Technical interpretations

- The relation is keyed by `(file_id, recipient_id)`.
- Repeated cancellation of an already absent relation is a harmless idempotent request; it never removes another relation.
- The file stays `shared` while another recipient exists and becomes `private` when the last relation is removed. Ownership is unchanged in either state.
- The scope concerns subsequent server requests after cancellation commits; it does not add cancellation of an already running byte transfer.
- These choices implement the supplied rule without adding business objects or workflows.

## Known framework limitation

The user reports incomplete matching between Boolean-rule dependency `data` events and logical `guard` edges during replay. Preserve the frozen framework and its tests. Record actual rule evaluations, decisions, relation effects, and state frames; do not claim that this known animation/matching issue was repaired.
