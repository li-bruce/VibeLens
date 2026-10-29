# 第一版测试结果

初版设计确认：2026-10-28。浏览器验收与收尾：2026-10-29，Asia/Shanghai。

## 最终结论

第一版当前验收通过：12 项真实 HTTP 集成测试通过，headless Playwright 在隔离数据中原样复测的 11 项检查通过，最终固定地址上同样的 11 项检查也全部通过。当前无未通过的业务检查。

访问地址：<http://127.0.0.1:8767>。后台服务使用项目 `data/`，保留一份明确标注的 `demo-project-notes.txt` 合成演示文件：所有者林舟，接收者许宁，周岚未获授权。三个账号用户名分别为 `linzhou`、`xuning`、`zhoulan`，演示密码均为 `Demo123!`。

应用仅监听本机。若服务在会话中断或机器重启后停止，在项目目录执行 `python app.py --port 8767` 即可重新启动，数据和共享记录会保留。

## 验收证据

| 检查批次 | 结果 | 原始证据 |
|---|---|---|
| HTTP 集成测试 | 12/12 通过 | `http-test-v1.log`；`tests/test_app.py` |
| 恢复后首次 headless，隔离数据库 | 通过 6 项后中断，未完成验收 | `browser-resumed-isolated.log`；`browser-runs/v1-resumed-isolated/result.json` 及失败截图 |
| 同一应用及同一脚本原样重跑，隔离数据库 | 11/11 通过 | `browser-resumed-isolated-retest.log`；`browser-runs/v1-resumed-isolated-retest/result.json` |
| 最终固定地址 headless | 11/11 通过 | `browser-runs/v1-live-headless/result.json`；同目录 `screenshots/`、`downloads/` |

运行环境：Python 3.13.13、SQLite、Playwright、headless Chrome 156.0.8078.47。后端运行不依赖第三方包；Playwright 和 Chrome 仅用于测试。

## 通过项

1. 林舟在页面登录并上传，文件归林舟所有，上传后仅所有者可访问。
2. 尚未授权时，许宁直接下载返回 HTTP 403。
3. 林舟在页面选择已有用户许宁共享，所有者页面明确显示许宁的查看及下载权限。
4. 许宁在收到共享的列表中看到文件名、125 B 大小和共享者林舟。
5. 许宁点击页面下载取得真实文件，文件名和内容均正确。
6. 接收者页面没有转共享操作，直接伪造共享请求也返回 HTTP 403。
7. 周岚的收到共享列表没有该文件，直接请求下载返回 HTTP 403。
8. 页面重新加载后登录状态和数据库中的授权仍有效。
9. 390 × 844 窄视口没有页面整体横向溢出，截图已保存；这仅为网页布局检查，不增加移动端业务。
10. 许宁退出登录后，再次直接下载返回 HTTP 401。
11. 完整浏览器流程未捕获 JavaScript 异常。

HTTP 测试还覆盖：每个用户都可拥有自己的文件、浏览器无法指定上传所有者、非所有者不能共享、同名新文件不继承共享、重复共享保持一条授权、无效接收者拒绝、CSRF 与跨来源请求拒绝、上传限制、空文件、路径隔离和新服务实例读取原有数据。

下载文件 SHA-256：`0586fce88f67685d3652ce257f11404f89c9916a5f460271dc5e00648a648d7e`。最终下载原件在 `browser-runs/v1-live-headless/downloads/v1-recipient-demo-project-notes.txt`。

## 历史未通过与恢复

- 最早 HTTP 测试在系统重定向临时目录创建子目录时出现 `PermissionError: [WinError 5]`，当次未执行任何测试。将测试临时数据放入本项目 `review/.tmp/` 后，12 项测试通过。未因此修改业务权限。
- 2026-10-28 的早期浏览器尝试遇到 `ERR_CONNECTION_REFUSED`、`ERR_CONNECTION_TIMED_OUT`；原有 `browser-attempt-1-environment.log`、`browser-test-v1.log` 和服务启动日志保留。一次自动权限审核超时，该次浏览器命令未执行；后续获准执行的尝试仍遇到连接问题。没有将这些尝试标成通过。
- 当时曾在内置浏览器打开登录页并登录林舟，上传交互在会话中断时终止。旧的 `screenshots/v1-login.jpg` 保留，但不作为三账号流程完成证据。
- 2026-10-29 恢复后首次 headless 已完成上传、授权、接收者下载及周岚拒绝等 6 项检查，随后 Playwright 的 `APIRequestContext.get` 连接返回 `EADDRINUSE`，未完成剩余检查。错误、堆栈、已通过项和三账号失败时截图全部保留。
- 未改应用或脚本，直接重跑通过全部 11 项；之后固定地址再次完成全部 11 项。`EADDRINUSE` 的具体系统根因未进一步定位，不能把单次重跑解释为已修复某个应用缺陷。

## 未实施项与停止位置

初版无文件删除、在线预览、转共享、修改文件、团队、公开链接、审批或订阅。取消共享仍为下一轮需求，未实施、未标为已通过。下一轮须保留本版设计和证据，并单独验证页面不刷新时的新下载请求会在取消共享后被拒绝。

本轮不再进行功能迭代；等待用户发出取消共享任务。没有读取或使用 Skill、VibeLens、相邻项目、原会话，也没有与其他会话通信或发布、推送 GitHub。

## 复现

```powershell
python -m unittest discover -s tests -p test_app.py -v
python tests/browser_check.py
python tests/browser_check.py --base-url http://127.0.0.1:8767
```

第二条命令使用独立临时数据库；第三条在运行中的演示库留下新的合成样本。每次浏览器运行自动创建独立证据目录，保留成功或失败的结果与截图，不覆盖先前证据。需要明确目录名时可传 `--run-id`，已有目录会被拒绝覆盖。
