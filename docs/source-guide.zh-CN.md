# 源码导览

[English](source-guide.en.md) · [使用说明](usage.zh-CN.md) · [架构说明](refactor-multilanguage.md)

这份导览按实际执行路径介绍源码。维护中的实现位于 [skills/vibelens](../skills/vibelens/)，示例项目中的同名模块是安装副本，用于验证接入真实项目后的行为。

三维视窗与二维视窗使用同一份图和运行证据。`graph-inventory.js` 汇总各层内容，`graph-links.js` 连接明确的源码与运行锚点，`graph-layers.js` 管理层的分类；`spatial-model.js` 计算包含关系的跨层投影，`spatial-layout.js` 在后台线程布局，`spatial-renderer.js` 管理真实三维摄像机和绘制。`semantic-view.js` 统一键盘和辅助访问入口。模块边界与交互说明见[三维图说明](../skills/vibelens/references/spatial-graph.md)。

## 先找到对应目录

项目与框架的接入边界位于
[delivery/integration.py](../skills/vibelens/scripts/bo_observer/delivery/integration.py)。
`bo_integrate.py` 安装最小原生依赖，并与已安装 Skill 的源码核对；源码扫描仅将核对通过的框架副本排除出业务覆盖检查。
`observation/capture_bridge.py` 协调跨进程录制范围和队列排空，原生 `bo_capture` 客户端只处理这些观测操作。业务状态转换仍由项目执行。

`concept-flow-layout.js` 根据关系类型为 ELK 提供业务、状态和规则的布局方向，
`layout.js` 负责嵌套区域与位置保存。`concepts/presentation.py` 校验可选链路标签引用的节点、边和确认来源；布局不修改图中的实际关系。

概念建模从 [concepts/](../skills/vibelens/scripts/bo_observer/concepts/) 开始。
`model.py` 组合业务、状态和规则定义，`state.py` 校验状态语义，`semantics.py`
保存确认范围和变更。`binding.py` 与 `anchors.py` 核对原生状态、规则、源码绑定和独立测试断言，
`projection.py` 为页面生成明确的实现关联。这些模块不执行用户程序的状态转换。
`associations.py` 核对规则适用目标、转换副作用及完成要求；`runtime.py` 使用原始调用 ID、
因果引用、实际完成值和事务身份检查这些关联。`concept-containment.js` 将明确的包含关系
转换为显示区域，原始关系与原生归属保持独立。
命令入口为 [bo_concepts.py](../skills/vibelens/scripts/bo_concepts.py)，操作说明见
[概念模型](../skills/vibelens/references/concept-models.md)。

语义分类仍为业务、状态、规则、实现和数据。查看器通过 `implementation-planes.js` 将实现细化为**入口、工程结构、代码执行**三个阅读层次。接口、文件、函数的原始 ID 保持不变；观测调用、数值和数据访问归入代码执行。默认先展示三张概念图，旧配置中的筛选和隐藏条件会保留。
Python 的 `graph/classification.py` 与前端 `graph-classification.js` 通过一致性测试共用分类；
无法分类的节点保留诊断信息。`graph/source_identity.py` 让多个源码引用指向同一个声明，
采集节点和调用实例仍保留各自身份。`hidden-paths.js` 只为当前视图计算有类型的间接路径。

`observation/concept_context.py` 在绑定会话启动时校验并固定概念上下文，检测声明文件和路径变化；
录制保留自己的上下文。`workflow/concept_review.py` 在下一次编码前恢复已确认含义、依赖和待处理项。

规则部分从 [policy/definition.py](../skills/vibelens/scripts/bo_observer/policy/definition.py) 开始。`projection.py` 将共享条件和源码映射接入整体图；`runtime.py` 是可选的 Python 执行器，`bindings.py` 核对实际加载函数与当前源码。`evidence.py` 校验真实求值路径及原始图事件，`sync.py` 接入现有开发同步流程。操作说明见[共享规则网](../skills/vibelens/references/shared-policy.md)，可运行内容见[示例](../examples/policy-network/)。

图标与右键菜单的键盘操作位于 `assets/stategraph-viewer/controls.js`。
`i18n.js` 决定页面语言的优先级，`web/interface_language.py` 校验并保存对话语言。
它们不修改图身份或业务数据。清空记录由记录服务处理，只删除经过身份与版本校验的单条已停止记录。

数据库部分从 [data/contract.py](../skills/vibelens/scripts/bo_observer/data/contract.py) 的 JSON 校验开始，依次是 `catalog.py` 读取原生元数据、`projection.py` 生成同一张图的节点与关系、`sync.py` 更新与独立核验。`runtime.py` 和原生 `bo_data.mjs` 观察实际调用，`watcher.py` 切换已校验的 Web 图版本。记录、回放及个人配置继续使用现有共用服务。完整接口见[数据库接入说明](../skills/vibelens/references/database-observation.md)。

数据适配器通过同一探针的当前调用上下文，保留请求、数据库调用与事务内部调用之间的父子关系。Python 使用 ContextVar，Node 使用 AsyncLocalStorage；已结束或属于另一探针的上下文不会继承。适配器管理原生调用区间，探针负责发送事件。真实 SQLite 回归见 `tests/test_database_runtime.py`，Node 原生回调、并发隔离和采集事实的 Timeline 索引回归见 `tools/test_data_context.mjs`。

工程结构由 [code_graph/filesystem.py](../skills/vibelens/scripts/bo_observer/code_graph/filesystem.py) 扫描目录与文件，`manifests.py` 读取包依赖，`structure.py` 连接包含树并分析文件依赖与循环。`index.py` 把这些结果与函数、类、参数串联；`query.py` 提供局部检索，`service.py` 负责自动刷新、源码读取和独立核验。界面的“工程结构”查看目录与文件，“代码结构”继续下钻到符号。它们共享同一份索引，详见[接口说明](../skills/vibelens/references/code-structure.md)。

| 位置 | 负责什么 |
|---|---|
| [SKILL.md](../skills/vibelens/SKILL.md) | 开发对话、业务图确认、迭代检查的操作流程。 |
| [scripts/bo_observer/control](../skills/vibelens/scripts/bo_observer/control/) | 对话与项目范围、视图及回放计划校验，以及控制命令入口。 |
| [graph/relations](../skills/vibelens/scripts/bo_observer/graph/relations/) | 构图时登记关系，检查重复定义、汇总路径及条件；路径失效后恢复原边，原始 ID 始终保留。 |
| [scripts/bo.py](../skills/vibelens/scripts/bo.py) | 原生项目的启动、校验、源码检索与导出入口。 |
| [scripts/bo_stategraph.py](../skills/vibelens/scripts/bo_stategraph.py) | 独立状态声明、观测到的实例与完整关系结构导出。 |
| [scripts/bo_contracts.py](../skills/vibelens/scripts/bo_contracts.py) | 参数类型、状态层次、活动状态计算和声明的严格校验。 |
| [scripts/execution_contract.py](../skills/vibelens/scripts/execution_contract.py) | 并发活动、汇合、资源与运行配置的约束。 |
| [scripts/bo_observer](../skills/vibelens/scripts/bo_observer/) | 共用服务、语言适配、开发检查及 Web 支持。 |
| [source_scope.py](../skills/vibelens/scripts/bo_observer/source_scope.py) | 统一声明项目源码、依赖和产物范围，供扫描、执行映射检查和工程目录视图使用。 |
| [assets/stategraph-viewer](../skills/vibelens/assets/stategraph-viewer/) | 项目实际使用的图页面、布局、记录和回放。 |
| [schemas](../skills/vibelens/scripts/bo_observer/schemas/) | 各语言与服务之间使用的 JSON 协议。 |
| [examples](../examples/) | 可运行项目、业务逻辑和验收场景。 |
| [tools](../tools/) 与 [tests](../tests/) | 安装、同步安装副本、仓库验收。 |
| [docs/site](site/) | 产品介绍页和独立的浏览器示例演示。 |
| [docs/review](review/) | 历次验收材料。历史记录保留原文。 |

scripts 根目录下多数小文件负责转发导入或命令调用。需要修改实现时，沿着导入进入 bo_observer。独立状态模块及两个约束文件可以脱离观测服务导入。

## 按三条路径阅读

### 一次代码修改怎样更新到图中

1. [workflow/bo_sync.py](../skills/vibelens/scripts/bo_observer/workflow/bo_sync.py) 的 source_inventory 从项目范围枚举源码，maintenance_task 与上次验收基线比较。因此新增文件也在检查范围内。
2. [sources.py](../skills/vibelens/scripts/bo_observer/sources.py) 的 scan 分派 Python、JavaScript 等语言解析；只有文件和解析器版本都匹配时才复用缓存。无法确定的调用会保留。
3. [graph/code_structure.py](../skills/vibelens/scripts/bo_observer/graph/code_structure.py) 提取 Python 声明，并通过 enrich 把局部源码结构关联到上层节点。
4. [development.py](../skills/vibelens/scripts/bo_observer/development.py) 将业务含义问题交给用户确认，将未明确的实现关系交给编码阶段处理。
5. [workflow/change_sync.py](../skills/vibelens/scripts/bo_observer/workflow/change_sync.py) 检查当前候选、影响范围和评审记录。
6. [workflow/sync_verify.py](../skills/vibelens/scripts/bo_observer/workflow/sync_verify.py) 运行约定的观测与测试，分别报告映射、状态规则、业务断言和项目检查。

扫描与检查只更新诊断信息。只有当前候选通过完整验证后，accept 才推进验收基线。

关系模块按职责分为：[contract.py](../skills/vibelens/scripts/bo_observer/graph/relations/contract.py) 检查关系含义和上下文，[paths.py](../skills/vibelens/scripts/bo_observer/graph/relations/paths.py) 检索有类型且工作量受限的路径，[index.py](../skills/vibelens/scripts/bo_observer/graph/relations/index.py) 处理原子插入和判定，[model.py](../skills/vibelens/scripts/bo_observer/graph/relations/model.py) 接入构图及重新校验，[bo_relations.py](../skills/vibelens/scripts/bo_relations.py) 提供 JSON 文件接口。新增组合规则前先看[判定条件](../skills/vibelens/references/relation-insertion.md)。实际调用、传值和状态转移保留为直接关系。

[workflow/iteration_recall.py](../skills/vibelens/scripts/bo_observer/workflow/iteration_recall.py) 在编码前恢复约定、观测代码位置及受影响的图层。[observation_requirements.py](../skills/vibelens/scripts/bo_observer/workflow/observation_requirements.py) 按层整理扫描与采集要求，识别埋点 API，检查延迟取值和实际调用闭合。它们复用原有实现清单，不维护第二张图。

[observation/ownership.py](../skills/vibelens/scripts/bo_observer/observation/ownership.py) 单独校验执行归属，与文件等业务对象标识区分。严格闭合检查同时拒绝缺少归属的内部观测。Python ContextVar 和 Node AsyncLocalStorage 在原生调用中传递上下文；浏览器采集器可显式传递入口事件引用。真正的外部点事件在原有节点中声明。前端 `trace-evidence.js` 与 `trace-executions.js` 依据相同标识关联，不用时间接近程度推测。

[observation/capture_context.py](../skills/vibelens/scripts/bo_observer/observation/capture_context.py) 将真实调用边界转为不含业务值的记录，并提取局部观测需要的父调用。`session.py` 独立保留有数量上限的执行中入口，批量预检复制这份缓存；普通历史过期不会直接丢失入口。`recording_session.py` 保留选中的值及所需边界，Python/Node 采集器跳过未选取值函数。`replay-steps.js` 将边界排除在普通回放步骤外，Timeline 仍按实际区间呈现调用。

### 一次业务操作怎样进入运行图

1. 应用完成业务判断，通过 [Python BOProbe](../skills/vibelens/scripts/bo_observer/adapters/python/bo_probe.py) 或 [JavaScript BOProbe](../skills/vibelens/scripts/bo_observer/adapters/javascript/bo_runtime.mjs) 提交指定参数。
2. 适配器筛选采集字段、抑制观测自身的事件，并排队发送。传输失败单独计数。
3. [protocol.py](../skills/vibelens/scripts/bo_observer/protocol.py) 校验项目、构建版本、类型及消息大小。
4. [observation/session.py](../skills/vibelens/scripts/bo_observer/observation/session.py) 的 GraphSession.event 保存事件标识、来源顺序和依赖；snapshot 将真实状态关联到对应事件。
5. [bo_stategraph.py](../skills/vibelens/scripts/bo_stategraph.py) 的 bo_observe 对照声明检查实际状态及版本。实际状态与声明冲突时保留原始事实并报告差异。
6. [observation/recording_session.py](../skills/vibelens/scripts/bo_observer/observation/recording_session.py) 保存指定时间段及缺失信息。view/export 返回结构和保留的运行事实。

驱动模式还会在应用自身调用 BOExecutor.step，依据声明求取下一状态；观察模式由应用自己的逻辑决定。两种模式遵守相同的观测协议。

### 一次点击怎样改变图的显示

| 文件 | 阅读重点 |
|---|---|
| [edge-color.js](../skills/vibelens/assets/stategraph-viewer/edge-color.js) | 图与时间轴共用连线配色：同层使用层颜色，跨层使用灰色，流动箭头沿用所在连线的颜色。关系线型由 `layout.js` 管理。 |
| [viewer.js](../skills/vibelens/assets/stategraph-viewer/viewer.js) | 页面按钮、数据刷新和记录选择的连接入口。 |
| [graph-core.js](../skills/vibelens/assets/stategraph-viewer/graph-core.js) | 节点值、源码关联、事件筛选与图内容。 |
| [trace-lifecycles.js](../skills/vibelens/assets/stategraph-viewer/trace-lifecycles.js)、[graph-activation.js](../skills/vibelens/assets/stategraph-viewer/graph-activation.js) | 解析真实调用周期，呈现进入、等待、返回、异常退出及并发数量。 |
| [trace-residencies.js](../skills/vibelens/assets/stategraph-viewer/trace-residencies.js)、[trace-flows.js](../skills/vibelens/assets/stategraph-viewer/trace-flows.js) | 呈现原生状态和任务的持续区间，以及调用、返回和状态转换。 |
| [trace-session.js](../skills/vibelens/assets/stategraph-viewer/trace-session.js)、[recording-timeline.js](../skills/vibelens/assets/stategraph-viewer/recording-timeline.js) | 管理实时查看的数据边界，以及时间轴的深度、选区、缩放和共同定位。 |
| [layout.js](../skills/vibelens/assets/stategraph-viewer/layout.js) | 展开收起、分组位置、筛选和批注。 |
| [view-lifecycle.js](../skills/vibelens/assets/stategraph-viewer/view-lifecycle.js) | 项目视图的稳定标识，以及录制与当前图版本的匹配。 |
| [renderer.js](../skills/vibelens/assets/stategraph-viewer/renderer.js) | Pixi 绘制和鼠标可命中的区域。 |
| [caption-layout.js](../skills/vibelens/assets/stategraph-viewer/caption-layout.js) | 按实际文字宽度适配节点标签，保留完整名称和已保存布局。 |
| [recording.js](../skills/vibelens/assets/stategraph-viewer/recording.js) | 回放步骤及运行证据支持的连线传递。 |
| [recording-timeline.js](../skills/vibelens/assets/stategraph-viewer/recording-timeline.js) | 时间轴面板、鼠标与键盘交互；通过同一个回放游标联动 Graph。 |
| [trace-evidence.js](../skills/vibelens/assets/stategraph-viewer/trace-evidence.js) | 图动画与时间轴共用的调用身份和父调用判定。 |
| [trace-index.js](../skills/vibelens/assets/stategraph-viewer/trace-index.js) | 调用耗时配对、事件依赖索引和跨层映射。 |
| [trace-executions.js](../skills/vibelens/assets/stategraph-viewer/trace-executions.js) | 按实际调用根识别执行链，为并发分组，每层保留一行，结束后复用同一组行。 |
| [node-lifecycle.js](../skills/vibelens/assets/stategraph-viewer/node-lifecycle.js) | 解析节点注册的事件、值与生命周期含义，提供通用执行描述。 |
| [trace-bars.js](../skills/vibelens/assets/stategraph-viewer/trace-bars.js)、[trace-routing.js](../skills/vibelens/assets/stategraph-viewer/trace-routing.js)、[trace-tooltip.js](../skills/vibelens/assets/stategraph-viewer/trace-tooltip.js) | 持续区间、圆角连线及其命中与动画位置，以及对应事实的悬停详情。 |
| [trace-density.js](../skills/vibelens/assets/stategraph-viewer/trace-density.js) | 将过密的短区间显示为像素计数；选中或放大后保留各区间的实际边界。 |
| [trace-viewport.js](../skills/vibelens/assets/stategraph-viewer/trace-viewport.js)、[trace-paint.js](../skills/vibelens/assets/stategraph-viewer/trace-paint.js) | 时间窗口运算、范围检索及可见区域绘制。 |
| [runtime-frames.js](../skills/vibelens/assets/stategraph-viewer/runtime-frames.js) | 查找事件对应的精确快照，比较状态和资源。 |
| [replay-steps.js](../skills/vibelens/assets/stategraph-viewer/replay-steps.js) | 按当前观察层级展示相关变化。 |
| [preferences.js](../skills/vibelens/assets/stategraph-viewer/preferences.js) | 通过项目接口保存个人显示配置。 |
| [polling.js](../skills/vibelens/assets/stategraph-viewer/polling.js) | 串行刷新及暂停、销毁控制。 |

完整模型、当前视图、运行证据各自保存。筛选视图保留完整模型，移动节点或回放记录仅改变显示。

## 修改和排版约定

源码关系由 [code_graph/index.py](../skills/vibelens/scripts/bo_observer/code_graph/index.py) 生成，query.py 提取局部和边界，service.py 管理索引刷新、版本校验和源码读取。用户可以按需打开“局部代码”或“代码结构”。静态连线与实际运行记录分别保留。

[session_lifecycle.py](../skills/vibelens/scripts/bo_observer/session_lifecycle.py) 管理每个请求使用的图版本。切换版本后，旧会话在最后一个请求完成时释放；耗时的源码解析和响应写入不占用全局会话锁。

[data/evidence.py](../skills/vibelens/scripts/bo_observer/data/evidence.py) 统一数据操作和功能映射中的证据校验。它按实际结果检查字段，例如失败时的错误类型、已知行数、事务提交或回滚；普通功能的采集字段检查继续保持严格。

主要函数用英文说明用途，在容易误读的位置解释顺序、所有权和失败处理。校验、状态修改等操作分行展开。源码可读性调整保持公开名称、协议字段、图 ID 及受保护的验收要求。

先修改主 Skill 的源码，再用 tools/sync_runtime.py 更新示例中的安装副本；项目自身的定义、数据和个人配置保留。第三方资源与历史验收材料保持原样。

[tools/formatting](../tools/formatting/) 固定开发用排版工具版本，与运行依赖分开：

    python -m pip install -r tools/formatting/requirements.txt
    npm ci --prefix tools/formatting
    python tools/format_source.py
    python tools/format_source.py --check

排版范围是维护中的 Python 模块、图页面 JavaScript、原生 JavaScript 适配器和产品页面。第三方 Pixi/ELK、示例安装副本、测试和历史材料不在排版范围。

纯可读性修改可以与指定提交比较可执行语法树：

    python tools/check_readability_equivalence.py --base <commit>
    node tools/check_js_readability_equivalence.mjs --base <commit>

JavaScript 比较使用原生适配器开发依赖中的 TypeScript。比较排除注释、文档字符串和行号，还需要运行实际行为验收：

    python tools/check_package.py
    python tools/verify.py

安装模块更新后，示例项目需要重新生成源码关联、检查候选、执行 verify，再 accept/check，并生成一份新的验收记录。

Canvas 图层工具的排序和显隐交互集中在 `layer-ruler.js`，统一间距由底部工具栏调整；坐标和圆周端点计算在 `edge-routing.js`；回放的跳步和循环范围规则在 `replay-selection.js`。这些模块只维护显示和个人设置，录制事实仍由原有记录模块保存。

## Routing and node icons

[source_documentation.py](../skills/vibelens/scripts/bo_observer/graph/source_documentation.py)
提取源码注释，检查映射函数、API 处理函数和重要参数的说明。它与代码索引共用处理函数的解析结果。
端点注册、处理函数和采集锚点保留各自的身份与关联。

[code_graph/observation.py](../skills/vibelens/scripts/bo_observer/code_graph/observation.py)
按处理函数、方法和路由确认观测来源；`api-observation.js` 为运行图、回放和时间轴共用这些精确关联。
API 最小结构独立于完整代码索引，录制开始时冻结保存，运行检查点不重复扫描源码。

[containment-geometry.js](../skills/vibelens/assets/stategraph-viewer/containment-geometry.js)
拟合可见文字、图标及子圈，`containment-view.js` 在筛选后重建可见包含关系。
三维相机与投影标记使用实际显示对象的边界；隐藏父节点的坐标继续保存，但不扩大显示范围。
[proximity-layout.js](../skills/vibelens/assets/stategraph-viewer/proximity-layout.js)
为二维、三维布局提供有上限的源码邻近提示，保留手动位置，不生成语义关系。

The shared viewer pipeline is `routing-scene.js` (renderer adapters), `routing-client.js` / `routing-worker.js` (epochs and lifecycle), `routing-engine.js` (routing and typed bundles), `routing-navigation.js` (reusable A* channels), and `routing-geometry.js` (R-tree checks and certified smoothing). `route-picking.js` resolves shared strokes to original edges. `node-icons.js` is generated from selected Tabler vectors; `glyphs.js` and `spatial-geometry.js` draw the same vocabulary in 2D and 3D. Rebuild pinned dependencies with `tools/routing/build.mjs` and icons with `tools/routing/build-icons.mjs`.

二维类型聚集由 [cluster-layout.js](../skills/vibelens/assets/stategraph-viewer/cluster-layout.js) 和其 worker 负责；[route-shapes.js](../skills/vibelens/assets/stategraph-viewer/route-shapes.js) 统一处理直线、曲线和连续虚线；[spatial-geometry.js](../skills/vibelens/assets/stategraph-viewer/spatial-geometry.js) 组合立体对象，供批量绘制和图例共同使用。图层选择在 Canvas2D 中绘制，间距统一由底部调整。

## v0.8.0 模块边界与检查

- `bo_observer/service.py` 负责 HTTP 鉴权、路由和会话借用；[observation/session.py](../skills/vibelens/scripts/bo_observer/observation/session.py) 负责事件接收、版本、因果关系和一致的状态帧。旧的 `service.GraphSession` 导入继续可用。
- [data/schema_compare.py](../skills/vibelens/scripts/bo_observer/data/schema_compare.py) 独立比较数据库结构；`data/projection.py` 负责把结构投影到图中。
- 前端 `viewer.js` 连接交互与数据；[detail-panel.js](../skills/vibelens/assets/stategraph-viewer/detail-panel.js)、[edge-panel.js](../skills/vibelens/assets/stategraph-viewer/edge-panel.js)、[change-panel.js](../skills/vibelens/assets/stategraph-viewer/change-panel.js) 分别显示源码与值、关系、步骤变化。面板把选择操作交回协调模块，避免直接修改模型和录制。
- 变化面板默认只显示两条变化，展开后查看全部原始值。[change-panel-position.js](../skills/vibelens/assets/stategraph-viewer/change-panel-position.js) 单独处理拖动和画布边界；拖动、收起面板均不会移动图中的节点，也不会影响采集。
- 源码面板只缓存当前构建和源码版本的文件。异步响应过期或用户已切换节点时，丢弃旧结果。

维护者运行：

```sh
python tools/check_source.py --format
python tests/test_source_quality.py
node tools/test_detail_panel.mjs
python tools/verify.py --database
```

[统一源码范围](../tools/source-scope.json) 同时用于格式化、lint 和语法对照。排除开源分发包、生成图标、示例安装副本和历史证据。Ruff 检查 Python 名称和控制流错误，ESLint 检查 JavaScript 名称、重复键等问题；Windows 和 Linux CI 使用相同的固定版本。新增或迁移模块会被语法对照报告为变化，需要明确审查和运行测试，不能用格式检查代替业务或映射验收。

发布前暂存候选版本，再运行 `python tools/check_release_export.py --staged`。CI 检查 `HEAD`：导出两个示例，只恢复已冻结的验收记录，并运行严格的 `check`。这个过程不重建图、不重新批准变更，可发现换行转换、漏提交文件等本地运行不容易暴露的问题。

HTTP 等待测试通过现有检查钩子暂停真实任务，观察到“运行中＋等待中”后释放。状态、函数和 SQLite 写入仍由程序实际执行，保留原有断言。


## 图层和录制的读取边界

- `graph-classification.js` 统一业务、状态、规则、实现、数据五类视图；API、工程结构、函数和数据操作保留为实现视图的筛选项。`layer-style.js` 统一顺序和颜色，形状表示节点类型。未分类内容单独显示，便于发现映射遗漏。
- `layout.js` 用 ELK 排列层与类型分组，`cluster-layout.js` 和 worker 用 D3 排列组内完整子树；两种视图共用初始平面坐标。
- `trace-tracks.js` 在同一层行内错开并发区间；`step-hierarchy.js` 按真实父调用缩进记录条目，并显示层颜色。
- `code_graph/service.py` 单独维护文件与导入关系，完整符号分析仍按需加载。开始录制时保存文件树，旧记录使用当时保存的树。
- 录制列表、读取和清除只检查当前图版本；周期检查点读取运行事实；实时图仍检查源码。它们共用 `GraphSession`，分别读取所需内容。
- `event_batch.py` 完成逐条预检与批次前后源码检查后，一次提交游标；`bo_retention.py` 批量写入日志，保持逐条通知、错误计数和原有文件轮转规则。

## 发布适配模块

完整 Skill 位于 `skills/vibelens/`。`plugins/deepseek-harness/` 负责宿主注册与当前对话绑定；`distributions/skillhub/` 处理目录平台的文件数限制，在本地校验并解包资源。`tools/build_distribution.py` 打包同一份源码并输出校验信息。`tools/harness-tests/` 检查真实宿主的调用流程，`tests/test_distribution.py` 检查包内容、对话隔离及篡改拒绝。
