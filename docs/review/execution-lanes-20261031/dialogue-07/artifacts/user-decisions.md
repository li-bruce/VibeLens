# User instruction provenance

## Explicit freeze instruction from the coordinating conversation

> 必须保留最小父边界后再通过。选择局部是缩小采集和展示范围，我仍然需要知道这次权限判断属于哪一次实际操作；未选节点的业务参数不用采集。页面如实显示缺失是正确的诊断，但不能作为这项功能已经完整的验收结果。请先冻结本轮全部实际证据，停止在 accept 和业务迭代之前，保留最新 source/runtime、旧基线、已保护断言、当前原始录制以及全部失败/修复/复测材料。将单权限聚焦导致父入口丢失列为共享采集/录制问题，保留已通过完整录制与 591 闭合检查的区别。等待维护仓库补齐最小真实边界并回归后，再开新对话。不要在试用工程中修改受管框架或扩大所选业务字段。核对完整命令后只关闭本轮拥有的服务，写明未完成项目与新的 RESUME.md。

## Later direct answer to the pending acceptance question

Question:

> 单权限节点的局部录制已采到真实规则点，但只保留了 parent_call_id，未保留对应父入口；Timeline 明确显示“归属待确认”，没有伪造成业务执行。此边界是否必须补齐父执行的最小上下文后才能通过 v1 验收？

Latest answer:

> 允许如实标示归属缺失的局部录制

The later answer changes the focused-recording acceptance criterion. It does not explicitly revoke the freeze or authorize accept. This round remains frozen without acceptance. Missing ownership is documented as a shared capture/recording limitation, and never reported as complete causal mapping. Preserve both instructions when resuming; honor the latest direct answer rather than silently reinstating the earlier stricter criterion.
