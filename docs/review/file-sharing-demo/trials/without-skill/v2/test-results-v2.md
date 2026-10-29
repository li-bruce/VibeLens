# 第二版测试与交付结果

日期：2026-10-29，Asia/Shanghai。状态：完成。

## 结论

20 项 HTTP 集成测试全部通过（V1 原有 12 项 + 取消共享新增 8 项）。headless Playwright 的 22 项检查全部通过（原流程 11 项 + 取消共享 11 项），隔离数据库及实际交付地址均已执行。当前未通过项为零，本轮没有因失败修改或放宽测试断言。

应用：<http://127.0.0.1:8767>，沿用现有 SQLite 和上传目录，未删除 V1 数据。账号及演示密码不变：`linzhou`、`xuning`、`zhoulan`，密码 `Demo123!`。

## 真实旧页面证明

固定地址上的取消共享样本是文件 ID 3，`revocation-sample.txt`，所有者林舟。

1. 许宁已通过页面下载成功，继续保持原收到共享页面打开。
2. 林舟通过页面取消给许宁的共享，后端返回 200 后所有者列表移除许宁授权。
3. 许宁的文档 `performance.timeOrigin` 未变；取消过程中，许宁页面没有发出任何新请求，原文件行和下载按钮仍可见。
4. 许宁点击旧按钮，通过浏览器捕获的真实 `GET /api/files/3/download` 返回 403。该阶段唯一的接收者请求就是这次下载，没有刷新文档、重新请求列表、轮询或重新登录。
5. 页面显示 `You do not have access to this file.`；浏览器下载事件数为零，没有产生新下载文件。
6. 林舟在取消之后通过页面下载同一文件成功，字节与许宁取消前下载的内容完全一致。
7. 许宁主动刷新后，已取消文件从收到共享列表消失。重新共享后可以再次下载；再次取消后最终状态保持所有者有文件、许宁无权访问。

原始证明位于 `browser-runs/v2-live-headless/result.json` 的 `revocation.stale_page_proof`，包含请求序列及事件计数；相应页面见该目录的 `revocation/screenshots/`。

## 证据位置

| 批次 | 结果 | 文件 |
|---|---|---|
| JavaScript 语法检查 | 通过 | `node --check static/app.js`，退出码 0 |
| HTTP 全部测试 | 20/20 通过 | `http-test-v2.log` |
| headless 隔离数据验收 | 22/22 通过 | `browser-v2-isolated.log`；`browser-runs/v2-isolated-headless/result.json` |
| headless 固定地址验收 | 22/22 通过 | `browser-runs/v2-live-headless/result.json` |
| 固定地址旧页面下载被拒绝截图 | 已保存 | `browser-runs/v2-live-headless/revocation/screenshots/v2-stale-download-denied.png` |
| 固定地址所有者仍可下载截图 | 已保存 | `browser-runs/v2-live-headless/revocation/screenshots/v2-owner-still-downloads.png` |

每次浏览器运行包含 5 张原流程截图和 7 张取消共享截图。取消前、所有者取消后、接收者旧页面、拒绝提示、所有者成功下载以及接收者刷新后的视图均保留。测试失败时会另存部分结果、堆栈和页面截图，本轮两批浏览器运行均直接通过。

取消共享样本的三份实际下载（取消前许宁、取消后林舟、重新共享后许宁）位于 `browser-runs/v2-live-headless/revocation/downloads/`，SHA-256 均为：

`2e73eb3aaa2eaa9bdc3358c4933e59125ce8157734a2aa3d200c5110c9ace41e`

运行环境：Python 3.13.13、SQLite、Playwright、headless Chrome 156.0.8078.47。测试使用真实 HTTP、真实 SQLite、浏览器点击及真实下载文件，没有模拟成功响应。

## 权限和回归覆盖

- 只有所有者能取消；接收者和其他用户即使直接发送带有效会话及 CSRF 的取消请求，也返回 403。伪造所有者字段不起作用。
- 未登录取消返回 401；缺少 CSRF、跨来源请求返回 403；这些拒绝不会改变原有授权。
- 取消仅影响一名接收者对一个文件的授权，其他已授权接收者和另一份文件的授权保持可用。
- 取消后文件记录、所有者及磁盘内容保留，所有者仍能下载；新服务实例读取同一数据库时仍拒绝已取消用户。
- 重复取消保持成功；重新共享仍按原流程生效；无效接收者及不存在的文件不会伪装成成功。
- 原上传、显式共享、接收列表、下载字节校验、禁止转共享、周岚拒绝、登录恢复、退出失效和网页布局检查均回归通过。

固定地址验收另外留下文件 ID 2 的原流程合成样本，并保留 V1 原有文件 ID 1；二者仍共享给许宁。ID 3 是本轮取消共享的独立样本，最终未共享。相同名称的回归文件是独立上传，不会互相继承或撤销权限。

## 基线、对话与停止位置

V1 压缩包、摘要清单、问答、原始用户回答、失败及复测证据全部保留。修改前全部 15 个基线文件摘要匹配，压缩包 SHA-256 为 `0ab249022c995e00e5313b42575432256e21943e35cbcdfd96a90ca0dc1178f2`；之后原压缩包仍保持该摘要。

本轮需求及回复保存于 `iteration-v2-dialogue.md`；设计变化见 `design-v2.md`。源码差异另存 `v1-to-v2.diff`，V2 源码另行封存，不覆盖 V1。

本轮完成后停止。未增加删除文件、在线预览、团队、公开链接、审批或订阅；未读取或使用 VibeLens、Skill、相邻项目或其他会话，也未发布或推送 GitHub。

## 复现

```powershell
python -m unittest discover -s tests -p 'test_*.py' -v
python tests/browser_check_v2.py
python tests/browser_check_v2.py --base-url http://127.0.0.1:8767
```

不带地址时使用隔离临时数据库；带地址时在运行中的本机演示库创建合成样本。每次运行使用独立证据目录，不覆盖旧记录。
