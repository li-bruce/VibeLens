# 隔离受控故障定位与修复记录

日期：2026-10-29，Asia/Shanghai。状态：已完成，测试服务已停止。

本轮是用户指定副本上的受控故障测试，故障在本轮开始前已存在。本文不将其写成自然发现的业务缺陷，也不据此改变原交付项目的验收结论。

操作范围仅为 `diagnosis-without-skill-20261029` 副本。原交付项目、其他试验、维护仓库和其他对话均未访问或改动，未使用 Skill，未推送。

## 原因与单点修复

副本 `app.py:353` 的取消语句为：

```python
db.execute("DELETE FROM shares WHERE file_id = ? AND recipient_id = ?", (file_id, user["id"]))
```

此处 `user["id"]` 是已登录的文件所有者 ID，`recipient_id` 才是用户选中的接收者 ID。所有权检查已正确完成，但删除条件把所有者当成了接收者。

在实际复现场景中，林舟是 ID 1，许宁是 ID 2，周岚是 ID 3。文件 ID 1 的共享记录为 `(1, 2)` 和 `(1, 3)`。错误语句尝试删除 `(1, 1)`，没有匹配记录。随后接口仍返回 `200 / shared: false`，页面也显示取消成功；许宁的授权实际上保留，下载路由按现存授权继续返回 200。

唯一的应用源码修改是：

```diff
-                db.execute("DELETE FROM shares WHERE file_id = ? AND recipient_id = ?", (file_id, user["id"]))
+                db.execute("DELETE FROM shares WHERE file_id = ? AND recipient_id = ?", (file_id, recipient_id))
```

没有改变原测试、断言、预期值、前端或数据库结构。重复取消保持原有幂等语义；不增加根据影响行数判断失败的行为。

## 修复前重现

1. 原有完整 HTTP 测试在本轮重新运行：20 项中 4 项失败，均为取消后下载实际返回 200、预期为 403。与用户提供的 `diagnosis-red-tests.json` 一致。
2. headless 浏览器通过真实页面上传文件，分别共享给许宁和周岚。
3. 许宁下载成功后保持原页面打开。林舟点击取消给许宁的共享，接口返回 200，页面显示取消成功。
4. 直接读取副本测试数据库：取消前后均保留 `(1, 2)`、`(1, 3)`；文件记录也未变。
5. 许宁没有刷新或重新获取列表，在同一份文档中点击旧按钮。仅发出一次真实下载请求，返回 200，产生 1 次下载事件，取得的文件与取消前内容一致。
6. 追加定位检查保留固定的业务预期 403、零下载事件以及目标授权移除，因此该轮明确失败。没有为了完成证据采集而把实际的 200 改成可接受结果。

原始测试失败保存在 `red/http-tests.json`、`red/http-tests.log`。旧页请求、数据库前后快照、取消响应及逐项实际/预期值保存在 `red/browser-result.json`；截图和误下载原件位于 `red/witness/`。

## 修复后复测

| 验证组 | 修复前 | 修复后 |
|---|---|---|
| 原有 HTTP 测试 | 20 项，4 失败 | 20/20 通过 |
| 补充定位检查 | 19 项，4 失败 | 19/19 通过 |
| 原有浏览器回归 | 本轮修复前未重复执行全套 | 原上传/共享/下载等 11 项通过 |
| 原有取消共享浏览器检查 | 本轮修复前未重复执行全套 | 原有 11 项通过 |

额外定位场景和原有浏览器检查存在覆盖重叠，分别列出，不把数量当作独立业务场景数量。

修复后已直接确认：

- 取消返回成功后，数据库仅移除许宁的 `(file_id, 2)` 授权，周岚的 `(file_id, 3)` 保留。
- 许宁保持原文档，取消过程中不请求新列表，旧文件行仍可见；点击旧按钮返回 403，下载事件为零，页面显示无权访问。
- 林舟仍能下载原文件，文件内容及所有权保留。
- 周岚作为仍被授权的另一接收者，继续下载相同内容。
- 许宁主动刷新后，已取消文件消失；林舟可通过原有界面重新选择许宁共享，许宁再次下载成功。
- 原有测试还验证其他文件权限不受影响、取消持久化、非所有者不能取消、未登录和 CSRF 拒绝、重复取消及原有上传下载行为。

修复后的原测试输出在 `green/http-tests.json`、`green/http-tests.log`；浏览器结果在 `green/browser-result.json`，其中 `original_regression` 和 `original_revocation` 是直接复用原测试函数得到的结果。原测试四个源文件的 SHA-256 均与修复前一致。

## 隔离与证据边界

- 复现与复测依次使用 `127.0.0.1:8854`，每轮分别使用 `red/browser-data/` 和 `green/browser-data/`，未使用副本默认数据目录或原交付数据库。
- 浏览器为 headless Chrome，所有成功和失败均由真实 HTTP、SQLite、浏览器操作和下载文件产生，没有模拟成功响应。
- 两轮浏览器服务均在脚本结束时关闭；没有留下新的常驻应用或对原交付服务进行操作。
- `before/faulty-source.zip` 和 `before/app.py` 保留故障状态；`after/repaired-source.zip` 和 `after/app.py` 保留修复状态；`repair.diff` 展示实际源码差异。
- 原始需求见 `request-original.txt`，执行摘要见 `timeline.md`，全部证据的摘要清单见 `evidence-inventory.json`，源码及原测试不变的校验见 `verification.json`。
- 用户说明故障注入前副本已通过原有 20 项测试。随副本提供的 `baseline-tests.log` 实际只记录 12 项通过，已原样保存在 `before/provided-baseline-tests.log`；本文不将它写成独立核验过的 20 项故障前基线。本轮红、绿两次均确实运行了完整 20 项。
- 封存工具首次把通用参数片段用于唯一性计数，该片段也出现在下载鉴权中，因此校验中断。已保留 `finalize-record-attempt-1.py` 和 `packaging-attempt-1.json`，改为逐字匹配完整取消 SQL 后重新封存。这仅修正证据工具的匹配范围，不改变应用修复、独立测试或任何业务预期。

## 复现方式

在副本目录运行：

```powershell
python review/diagnosis/run_checks.py http --phase green
python review/diagnosis/run_checks.py browser --phase green --port 8854
```

已保存的浏览器目录不允许原地覆盖；需要重新执行时，应在新的独立证据目录中运行同一检查。故障代码仅作为静态归档保留，不再将运行源码恢复为故障状态。本轮完成后停止，没有功能扩展。
