Repair18 正常录制后的验证失败与只读诊断交接（2026-11-20）

浏览器完整路径通过，但完整 verify 未通过；不接受初版，等待 repair19。未修改安装、规范、旧事件或失败后的业务源码，未重录或盲重跑，未启动新实时活动。

- APP：`C:\Users\Lvi_P\Documents\Work\CF\平台软著\SoftwareStatusObserverSkill\.validation\p7-trials\node-retest-app`
- candidate：`d2d0d83903b7d183813fcc28c4d11b4aadefdbfb940f5212de438dc08c190465`
- build：`483355a5043fcd82febc74d9accd73f15db23114fef8dcac970bcf25f6fac91f`
- provider：`C:\Users\Lvi_P\Documents\Work\CF\平台软著\SoftwareStatusObserverSkill\.validation\p7-trials\atomic-catalog-skills\vibelens`
- 原始失败报告相对 APP：`review/runtime/repair18-formal-recording-20261120/post-recording-verify/stdout.json`
- 错误分类：`review/runtime/repair18-formal-recording-20261120/post-recording-verify/failure-breakdown.json`
- 原浏览器驱动：`review/runtime/unified-1795184762`，完整未裁剪路径，七项通过。

录制与涉及案例

`browser` / `on` 的验证输入来自正常停止录制 `209889eb57cc4879b13a376f35e44513`（1264 事件、6 个 frame）。第二段完整 GUI 业务录制 `a2f1902bb843434f9ed72f986dab9121`（5196 事件、32 个 frame）也正常停止。两者 gaps=[]、flushed=true、pending=0；off/fault 的真实业务与文件结果一致。第二段未被偷偷替换成第一段的验证输入。

1358 项诊断及确切入口

| 诊断 | 数量 | APP 导出入口 | canonical 验证入口（相对 provider） |
| --- | ---: | --- | --- |
| native_event_invalid；source_seq/stream_id 为额外属性 | 1264 | tooling/browser_evidence.mjs:40 直接将 recording.events 放入原生 run.events | scripts/bo_observer/behavior/native_runtime.py:58；bo-event/v1 仍严格校验 |
| missing_state_snapshot | 6 | browser_evidence.mjs:32 的 snapshots=[] 未填；40 只附带 runtime_frames | scripts/bo_observer/workflow/snapshot_evidence.py:93 |
| missing_tracing_backend | 1 | browser_evidence.mjs:41 取 recording.final.health.producer 聚合值 | scripts/bo_observer/observation/telemetry.py:104 |
| policy evaluation belongs to another declaration | 83 | browser_evidence.mjs:45 保留实际 evaluation；实时 bo_create 使用旧 hash fallback | scripts/bo_observer/policy/evidence.py:72 |
| project test failed | 1 | 原 tooling/project_checks.py 严格检查失败，没有削减 | 见该命令原始 stdout/stderr |
| behavior_evidence_missing | 3 | 下游行为证据诊断，原样保留 | 见原始错误对象，不合并为成功 |

所有对应项在 browser/on 输入中定位；下游测试/行为项单独保留。mapping、project_checks failed；business、state_rules、concepts passed。database/code_structure/API/producer_health/invocation_closure/concept_associations 的独立结果 valid=true；严格 snapshot/behavior/policy 门禁仍失败。完整闭合检查 closed_calls=565、errors=[]。全部原断言、案例和 capture 范围未变。

策略哈希根因及候选修复

integrations/bo_observe.mjs:55 的 `options.policyHash || review/policy-fingerprint.json.hash` 形成双来源。bo_start:150 只从 collector 传 endpoint/token/build_id，没有传测试用的 policyHash，因此实时启动落到旧文件。实际旧值 `0bef0516679409c7052399a7c20647ae15205120c55621ac80514b9c5e29898b`；当前已绑定 policy 的 canonical fingerprint 为 `e0a2fb193c646dfc93c4dbfffbafa7f9d184c0896e12b01838f99f4d2e57fec0`。原生测试由 tooling/observe.py 传当前规范值，所以此前非浏览器检查通过。

bo_policy.py check 当前声明静态 valid=true。已核对可用共享 API：read_model、validate(bound=True)、fingerprint；没有自写 JSON 哈希。当前 collector 元数据只有 endpoint/token/build_id，JS SDK 没有独立的规范 policy fingerprint 接口。

候选实现已具体化于 policy-binding-root-cause-and-plan.json：让 bo_create 在实时和测试中统一取得并核对 canonical 当前绑定声明与 build；测试传值仅作一致性断言；删除旧 review 文件 fallback。用安装提供的 Python 共享 API/repair19 公共绑定接口做薄适配，绝不实现另一套 JS JSON 哈希或再次执行业务授权。等 repair19 安装后落实源绑定并生成新构建/新录制；本阶段尚未声称该源码修复已实现，也未改旧文件值。

只读核对结果

独立审计 audit_original_recordings_v2.py 使用 canonical instance_key（grant 中的 / 按规范编码为 %2F），没有改原对象。两段录制分别闭合 296、995 个调用；38 个原始 frame 的 model/native_instance/attempt/build 与原始事件联结成立。最终 12 个模型对象与正常停止时封存的实际 SQLite 镜像一致。实际 HTTP 202 → request_download → task_commit → SQL 的任务/请求者/文件/提交授权/transaction ID 对应，三个模式的实际上传/准备文件 hash 一致。Bob 任务 ready、授权=1、grant inactive，两次领取字节均与准备文件一致。

审计使用 query-only 内存 SQLite 反序列化已封存的真实持久化字节，不长期打开业务文件。它只证明所列原始归属/SQL/文件/调用事实，不修补 strict verify 的输入，也不替代失败结论。attempt 按实际 envelope 保留，未编造每任务 attempt；合法 active/ready 状态驻留不被伪称为结束。

额外原始计数仍保留：pre_cleanup_native_health 显示 OTel backend、open_spans=0、errors/dropped=0，同时 capture_control_errors=1。该累积计数未清零，也未从聚合 health 推造。

证据与当前状态

正常停止原件 ZIP SHA256：`6bd7839eb7e57447040c84053a9398e23dd92bf4726c2360b84c0aa6c75d11ec`；227 个源文件已封存。旧 EPERM 失败 ZIP 827f6c00…及诊断原件保持。2777 个新 provider 非缓存文件校验无变。只读审计结果见 independent-recording-audit.json。

按最新协调继续只读、等待 repair19：没有重写旧 bo-event、补 snapshot/backend/hash，没有新迭代/重录/accept，服务也尚未重启。修复后的完整验证和非空新实时历史/UI 交接仍待完成。
