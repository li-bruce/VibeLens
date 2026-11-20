SQLite catalog 与原生文件发布冲突：最小复现交接（2026-11-20）

诊断完成，等待根仓库修复并提供新独立安装。本轮未修改安装或业务 Store，未新增模式声明，未整段重试、延长等待、重写事件或补状态。

隔离复现

- 脚本：reproduce_sqlite_replace.py，SHA256 `7cfe07308dba3d796178396d81bc8b62c07941299e6619c3dbcf05ce1b503e49`。
- 原始结果：sqlite-handle-repro/result.json，SHA256 `aee0062f820bd2cc7ba41b67c87b0667ec705b31248ca5f7e8d7f8e6da8c0168`。
- 脚本为一次性隔离复现，拒绝覆盖已有 fixture；已执行的现场及其 reader/writer 源码全部保留。

从已封存的原数据库复制 fixture，writer PID 45036 导入未改动的 src/store.mjs，执行实际 Store.persist：无 collector 时替换成功，Restart Manager 无 holder。

独立 Python 进程调用本次安装 canonical collect；只在真实 get_table_names SQL 完成后设置进程局部屏障，不改安装或返回值。PRAGMA database_list 确认实际打开 fixture，读到六张表。Windows Restart Manager 唯一 holder 为 reader PID 18572。同一个 writer 此时真实 rename 失败：EPERM、errno -4048、syscall rename，与原事故一致。

释放屏障后 canonical collect 正常结束并 dispose；reader 进程保持存活。Restart Manager holder 已空，同一个 writer 随即替换成功。故无需连接泄漏，连接正常打开期间的重叠窗口已足够造成冲突。

归因边界：原事故未采集当时的 OS handle 快照，不能追认原 viewer PID 是已证明的历史 holder。这里证明的是配置中的具体共享路径及其足够复现同一错误的机制，诊断 holder 的 PID 已由 OS 确认。

具体共享路径与其他读者

bo_stategraph/databases.json 配置 engine=sqlalchemy，TEAM_FILES_SQLITE_URL 指向真实 var/db/application.sqlite。data/sync.py:131-132 仍调用 collect(store)，离线 declaration exporter 不会替代它。catalog.py:135 打开实际只读 SQLite reflection connection，169 在 finally 中 dispose。dispose 正确不能避免打开期间与 Windows rename 的冲突。

- tests/native_reader.mjs 与 browser_evidence.mjs 读取文件字节到内存 SQL.js，随后显式 database.close；不是长期 native SQLite 文件连接。
- bo_export_schema.py 使用 :memory: 并 dispose，不打开实际业务文件。
- transport_repro.py:16-19 有 finally database.close，而且本次 --recording 未执行该路径。
- 最早一次性业务快照命令用了 with sqlite3.connect 而未显式 close，依赖短进程退出释放；工具确认该进程在首轮 verify 和浏览器启动前已结束，未证明是录制期间持有者。

确认支持“完整 SQLite 文件原子发布”模式的源码依据

1. package.json:23 固定 sql.js 1.14.1。Store 构造时以 readFileSync 字节创建内存 SQL.Database（src/store.mjs:23）；业务 SQL 在内存执行。
2. Store.transaction 在同步 COMMIT 后调用 persist（75），无原生文件型 SQLite 写事务跨越发布阶段。
3. Store.persist 把 db.export() 的完整数据库镜像同步写到 this.filename + '.tmp'（82）；不是原地更新数据库页。
4. 随后 renameSync 把同目录完整临时文件发布到目标路径（83），这正是原失败的路径。src/server.mjs:9 为该服务创建一个 Store。
5. 本轮实际数据库、.tmp、以及未改动 Store.persist 的受控替换错误共同支持这条源绑定；不能泛化到事务型/WAL 写入者。新模式仍需显式声明，本轮未添加。

Store SHA256：`5b69d55d058c5a85a6b599d3626f056b09aa2702b6271c273805a6fb81ad2cb4`。原生事务/准备处理最大活动数为 1，只保留真实双请求 barrier 证据，不宣称并行 worker。

实际录制状态及封存

首次完整 verify 的四条命令均退出 0；valid=false 的 19 项仍是当时未运行浏览器的缺口。之后未削减 unified --recording / browser_acceptance 完整路径实际执行，on/off/fault 与上传共享通过。第一段 1155de8f7af248febb68c9c2778bb921 正常 stopped，1160 事件、gaps=[]、flushed=true。第二段 5ae95d6942d748cc9aa59d94080bdc30 中断，304 事件及真实 drain/scope 缺口保留；其余 GUI 用例未完成，不能计为全通过。

app.stderr.log 的 Store.persist EPERM 导致原生 worker 错误记录写入再抛出，应用在 unified 清理前已退出 1。worker 异常逃逸是独立的应用健壮性问题，未自行修改。

失败、数据库/.tmp、录制、日志与截图 178 个原文件保留在 failed-unified-original-evidence.zip，SHA256 `827f6c00d495c073c524f23e8ded8515fbbdbaac82a9c2c730d78bcc8b628d52`，诊断后逐一复核原字节无变。2776 个 provider 非缓存文件无变；业务源码、模型/capture/断言及检查命令无变。

candidate `e69ab132d4b5744650208f713c5675a8472963bbd0b3f73e3dd5eee391e1999c`；build `5dc7cccff1add8a3e1f4c89aea87f6e658ff47e8359ae284a76f61c3574a3fe5`；provider `C:\Users\Lvi_P\Documents\Work\CF\平台软著\SoftwareStatusObserverSkill\.validation\p7-trials\asset-transport-skills\vibelens`。按最新指令没有后续完整 verify、重录、服务重启或 accept。当前验收服务已由原 unified 清理；端口与原数据库当前 holder 核查见 diagnosis-summary.json。待新安装正常升级后，再恢复原完整用例及非空实时历史/UI 交接。
