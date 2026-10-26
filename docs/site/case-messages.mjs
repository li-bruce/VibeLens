/** Human-facing copy for the separate, evidence-backed project story. */
export const messages = {
  "case.application": [
    "See the running application: before and after",
    "查看实际运行的项目：修复前与修复后",
  ],
  "case.application.v1": [
    "First run · preview v1, published v2",
    "首版 · 打开的是第 1 版，发布的却是第 2 版",
  ],
  "case.application.v2": [
    "Repaired run · reopened v2, published v2",
    "修复版 · 重新打开第 2 版后，才发布第 2 版",
  ],
  "case.home": ["Product overview", "产品介绍"],
  "case.project": ["Run the project ↗", "运行示例项目 ↗"],
  "case.kicker": ["AFTERLIGHT · A RECORDED DEBUGGING STORY", "AFTERLIGHT · 一次真实录制的调试过程"],
  "case.title": ["The image nobody reviewed.", "那张没被审核过的图片。"],
  "case.lead": [
    "The upload works. The approval works. Together, they publish the wrong version. Follow the request through eight layers to see why—and watch the repair hold.",
    "上传正常，审核按钮也正常。两个操作交错，却发布了错误的版本。沿着一次请求逐层查看原因，再用新的运行结果检验修改。",
  ],
  "case.opened": ["v1 · opened for review", "第 1 版 · 审核者看过的图片"],
  "case.published": ["v2 · published unseen", "第 2 版 · 未经查看却被发布"],
  "case.provenance": [
    "Recorded from a runnable browser + Python + SQLite project. The first version contains a deliberately seeded defect; the dialogue is a scripted example. The graph and values below come from actual executions.",
    "示例由浏览器前端、Python 后端与 SQLite 实际运行并录制。首版缺陷为演示预设，对话为模拟；下面的图、参数与结果来自真实执行。",
  ],
  "case.chapters": ["Story chapters", "演示阶段"],
  "case.tab.0": ["1 · Confirm", "1 · 确认"],
  "case.tab.1": ["2 · Record", "2 · 记录"],
  "case.tab.2": ["3 · Find", "3 · 定位"],
  "case.tab.3": ["4 · Change", "4 · 修改"],
  "case.tab.4": ["5 · Retest", "5 · 复测"],
  "case.graph": ["Actual VibeLens viewer", "真实 VibeLens 图视窗"],
  "case.layers": ["Open all layers", "展开全部层"],
  "case.trace": ["One request, eight connected layers.", "沿着一次请求，串联八个层次。"],
  "case.trace.body": [
    "Follow approval from the API into the business flow, state, rule, selected values, database operation, tables and source. Use the layer shortcuts above, expand nodes, then open source from a node’s menu.",
    "从审核接口进入业务流，继续查看状态、判定、参数、数据库操作、表结构与源码。可点击上方图层入口、展开节点，再从节点菜单打开源码。",
  ],
  "case.diff": ["The repair, in the real source.", "在实际源码中看这次修复。"],
  "case.diff.label": ["Iteration 1 → iteration 2", "首版 → 修复版"],
  "case.diff.body": [
    "The rule now compares the version opened for review with the current version. The request, state and database write remain connected to the same graph identities.",
    "修复后的规则会比较审核者打开的版本与当前版本。请求、状态和数据库写入仍通过原有节点串联，便于对照两次运行。",
  ],
  "case.takeaway": [
    "A working button can hide a broken assumption.",
    "按钮能用，内部的假设也可能出错。",
  ],
  "case.takeaway.body": [
    "The recording puts the two versions side by side. The source shows the missing comparison. The next run shows whether the change worked. Bring that same view into your next coding conversation.",
    "运行记录让两个版本号同时可见，源码指出缺少的比较，下一次执行验证修改结果。你也可以带着这张图，在下一轮开发对话中准确描述问题。",
  ],
  "case.install": ["Use VibeLens in your project ↗", "在你的项目中使用 VibeLens ↗"],
  "case.practice": ["Try the small recording practice", "试试简短的录制练习"],
  "case.receipts": [
    "Read the dialogue, test results and screenshots ↗",
    "查看对话、测试结果与截图 ↗",
  ],
  "case.raw": ["Execution receipt ↗", "运行验收记录 ↗"],
  "case.help.2d": [
    "2D · Trace a local path. Double-click a node to expand; drag to arrange; right-click to inspect its values or source. Replay uses the recording bar.",
    "二维 · 适合追踪局部链路。双击展开，拖拽布局，右键查看参数或源码。使用录制条回放实际操作。",
  ],
  "case.help.3d": [
    "3D · Separate the same graph into layers. Drag empty space to orbit; use the left ruler to show, hide or reorder layers. Scroll to zoom.",
    "三维 · 将同一张图按层分开。拖动画布切换视角，左侧尺子控制图层显隐和顺序，滚轮缩放。",
  ],
  "case.next": ["Continue →", "继续 →"],
  "case.restart": ["Start again ↺", "重新查看 ↺"],
  "case.user": ["Developer", "开发者"],
  "case.assistant": ["Coding assistant", "开发助手"],
  "case.recorded": ["Recorded execution · iteration", "实际运行记录 · 第"],
};

/** Each paragraph explains the current graph focus, with a short scripted dialogue. */
export const chapters = [
  {
    title: ["First, agree on what approval means.", "先确认“审核通过”的含义。"],
    body: [
      "A small gallery needs uploads, image checks, review messages and an exhibition. One clarification determines what a correct approval must refer to.",
      "画展需要上传、图片检查、审核消息和展览页。一个必要的澄清，决定“通过”究竟对应哪张图片。",
    ],
    dialogue: [
      [
        "assistant",
        "If the artist replaces an image after the reviewer opens it, may the old approval publish the replacement?",
        "审核者打开图片后，如果上传者替换了图片，旧页面上的“通过”能发布新图片吗？",
      ],
      [
        "user",
        "No. The replacement must stay pending until the reviewer opens that version.",
        "不能。替换的图片要等审核者打开这一版后再通过。",
      ],
      [
        "assistant",
        "Should the state declaration drive the app, or observe its own logic?",
        "后续用状态声明驱动程序，还是保留程序自身逻辑并进行观察？",
      ],
      [
        "user",
        "Keep the app’s logic. Use SQLite locally. This flow matches what I mean.",
        "保留程序自身逻辑，本地用 SQLite。现在的流程图符合我的意思。",
      ],
    ],
    view: "business",
  },
  {
    title: ["Record the moment the two versions diverge.", "录下两个版本发生分歧的过程。"],
    body: [
      "The browser performs the full flow while the observer records actual requests, selected values, SQL operations and state snapshots. An ordinary upload-then-approve test would miss this ordering.",
      "浏览器实际完成整条流程，观察器记录请求、关键数值、SQL 操作和状态快照。只测“上传后立即审核”，容易漏掉这种交错顺序。",
    ],
    dialogue: [],
    view: "overview",
  },
  {
    title: ["Permission passed. The version was never checked.", "权限通过了，版本却没有检查。"],
    body: [
      "In the recording, approval carries version 1; the database read returns version 2. Follow the rule node into policy.py: it accepts the reviewer’s role and ignores both version arguments.",
      "记录中，请求携带第 1 版，数据库读出第 2 版。沿判定节点进入 policy.py，可以看到函数只判断审核者身份，没有比较这两个版本参数。",
    ],
    dialogue: [
      [
        "user",
        "I approved the blue image. Why is the orange one on the exhibition page?",
        "我通过的是蓝色那张，展览页怎么出现了橙色那张？",
      ],
    ],
    view: "permission",
  },
  {
    title: ["Change the comparison. Keep the rest of the flow.", "补上比较，保留原来的流程。"],
    body: [
      "The next coding iteration changes the native policy and refreshes its source-bound graph. The same nodes now expose the added version check; a new build has its own recording.",
      "下一轮修改原生判定函数，并更新与源码对应的图。原有节点中出现了版本检查，修复版使用自己的构建标识和运行记录。",
    ],
    dialogue: [
      [
        "user",
        "Reject an approval of a replaced image. Ask the reviewer to open the latest version. Keep uploads, messages and the exhibition flow as they are.",
        "拒绝对旧版本的审核，让审核者重新打开最新版。上传、消息和展览流程保持原样。",
      ],
      [
        "assistant",
        "I’ll compare reviewed_version with current_version before any exhibition write, then rerun the stale and fresh review cases.",
        "我会在写入展览前比较 reviewed_version 与 current_version，再复测旧版本和最新版本两种情况。",
      ],
    ],
    view: "permission",
  },
  {
    title: [
      "Replay the same attempt. Then finish a fresh review.",
      "重放同一操作，再完成一次有效审核。",
    ],
    body: [
      "The stale attempt now leaves the exhibition empty. After opening version 2, approval publishes version 2. Permission denial and invalid-image checks run alongside the repair case.",
      "旧页面上的审核被拒绝，展览没有新增内容。重新打开第 2 版后，审核才发布第 2 版；同时复测无权限审核和无效图片。",
    ],
    dialogue: [],
    view: "overview",
  },
];

export const layerLabels = [
  ["api", "API", "API", "#986345", "/app/approve"],
  ["business", "Business flow", "业务流程", "#208b73", "Approve opened image"],
  ["states", "States", "状态", "#8c57ad", "pending → displayed"],
  ["permission", "Rules", "判定", "#af731c", "approval_policy"],
  [
    "functions",
    "Functions & values",
    "函数与参数",
    "#477b9c",
    "reviewed_version / current_version",
  ],
  ["data-operations", "Data operations", "数据操作", "#3b839c", "read → select → write"],
  ["database", "Data structure", "数据结构", "#638b98", "artwork · images · exhibition · messages"],
  ["code", "Source code", "源码结构", "#8172a3", "app.py → domain.py → policy.py"],
];
