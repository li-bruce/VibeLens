# Simulated kickoff dialogue

Evidence class: scripted AI dialogue, not independent human feedback.
Scenario: a new Node frontend and Python backend project. No application is implemented by this trial.

**用户（模拟，U1）：** $vibelens，开始一个 Node 前端、Python 后端的新项目。目录你来建议。自己的模块为了本地保密会加进 .gitignore；review/manual-tests 里有真正调用应用代码的测试。

**助手（模拟，A1）：** 先把计划目录的用途记清楚，再扫描源码：

| 目录 | 用途及扫描范围 |
| --- | --- |
| web/、server/ | 项目自有前端、后端源码，扫描 |
| modules/private-core/ | 项目自有本地模块，扫描；加入 .gitignore 仍保留在源码范围内 |
| review/manual-tests/ | 项目自有测试代码，扫描 |
| node_modules/、.venv/ | 安装的依赖，进入目录前剪枝 |
| data/uploads/ | 上传文件内容，进入目录前剪枝 |
| review/runtime/ | 生成的运行证据，进入目录前剪枝 |

源码根保留 `.`，以便后续新建顶层源码目录也能发现；不把整个 data/ 或 review/ 排除。`.gitignore` 只作为范围判断的参考。以上计划会先写入同一份 sync.json；有不清楚归属的目录才需要确认。

还需选运行方式：让状态声明驱动执行（drive），还是应用保持自己的逻辑、图只作观察（observe）？两种方式都会维护图和监测。答复前可以准备目录和扫描范围，暂不实现业务行为。

**用户（模拟，U2，保留指定原话）：** 按你建议的目录建，项目上传的文件放data/uploads，自己的模块在modules/private-core。

**助手（模拟，A2）：** 目录范围已明确：modules/private-core/ 是自有源码，data/uploads/ 是上传内容；review/manual-tests/ 的测试保留扫描。不会因为私有模块被 .gitignore 忽略而漏掉它。运行方式仍待答复，先完成与模式无关的范围准备。

**用户（模拟，U3）：** 用 observe。

**助手（模拟，A3）：** 记录为 observe。先按上面的目录范围配置 sync.json，再做首次扫描；后续目录用途或 .gitignore 改变时复核同一份范围。这里尚无业务行为描述，业务图和实现留待你提出具体需求后确认。

Scope declaration used by the isolated fixture: `sync-planned.json`. This dialogue describes planned actions; only the separate fixture results establish executed checks.
