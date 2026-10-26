/** Short product copy; the review material carries the complete case history. */
export const messages = {
  "case.home": ["VibeLens", "VibeLens"],
  "case.install": ["Get VibeLens", "开始使用"],
  "case.eyebrow": ["VibeLens in action", "VibeLens 交互演示"],
  "case.title": ["See what your AI built.", "看清 AI 写出的程序。"],
  "case.lead": [
    "Define Afterlight in conversation. Explore its running logic in VibeLens. Bring the findings into your next change.",
    "在对话中构建夜幕，在 VibeLens 中观察运行，再带着发现继续修改。",
  ],
  "case.scroll": ["Scroll to follow the build", "向下，跟随一次开发"],
  "case.nav": ["Development stages", "开发阶段"],
  "case.confirm": ["Continue to development", "确认后进入开发"],
  "case.business": ["Business graph", "业务图"],
  "case.states": ["See the states", "查看状态机"],
  "case.build": ["Inspect the connections", "操作这张关系图"],
  "case.run": ["Replay the operation", "回放这次操作"],
  "case.drill": ["Open function source", "查看函数源码"],
  "case.save": ["Save my view", "保存观察视图"],
  "case.saved": ["View saved", "观察视图已保存"],
  "case.viewName": ["My approval path", "我的审核链路"],
  "case.name": ["View name", "视图名称"],
  "case.replay": ["Replay this path", "只回放这条链路"],
  "case.repair": ["Compare the repair", "查看本轮修改"],
  "case.retest": ["Run the same check", "查看复测过程"],
  "case.rule": ["Review rule", "审核规则"],
  "case.versions": ["Image versions", "图片版本"],
  "case.effects": ["Selection & write", "选版与写入"],
  "case.status": ["State changes", "状态变化"],
  "case.selected": ["Keep in this view", "保留在这个视图中"],
  "case.observer": ["VibeLens", "VibeLens"],
  "case.explore": ["Explore graph", "操作图"],
  "case.browse": ["Continue scrolling", "继续浏览"],
  "case.tools": ["Full tools", "完整工具"],
  "case.core": ["Core path", "核心链路"],
  "case.graph": ["Business flow", "业务流程"],
  "case.implementation": ["Implementation map", "实现关系"],
  "case.layered": ["All layers", "全部图层"],
  "case.paused": ["Play", "播放"],
  "case.pause": ["Pause", "暂停"],
  "case.position": ["Playback", "回放进度"],
  "case.conversation": ["Developing Afterlight · Codex", "开发夜幕 · Codex"],
  "case.location.codex": ["In Codex", "在 Codex 中"],
  "case.location.vibelens": ["In VibeLens", "在 VibeLens 中"],
  "case.location.project": ["In Afterlight", "在夜幕网站中"],
  "case.user": ["You", "用户"],
  "case.gestures": [
    "Drag to rotate · scroll to zoom · right-drag to pan",
    "拖动旋转 · 滚轮缩放 · 右键拖动平移",
  ],
  "case.app": ["Application replay", "业务界面回放"],
  "case.app.name": ["Afterlight", "夜幕"],
  "case.app.replay": ["Replay the application actions", "重放业务操作"],
  "case.app.seek": ["Jump to the next recorded action", "定位到下一次已录制的操作"],
  "case.app.artist": ["Upload", "上传"],
  "case.app.reviewer": ["Open", "查看"],
  "case.app.exhibition": ["Exhibition", "展览"],
  "case.app.approve": ["Approve", "通过审核"],
  "case.app.image": ["Image", "图片"],
  "case.app.empty": ["Awaiting upload", "等待上传"],
  "case.app.pending": ["Pending review", "待审核"],
  "case.app.displayed": ["Published", "已发布"],
  "case.app.stale_review": ["Open the latest image", "请重新查看最新图片"],
  "case.app.forbidden": ["Reviewer required", "需要审核权限"],
  "case.app.invalid_image": ["Invalid image", "图片格式无效"],
  "case.check.pass": [
    "Old preview rejected · latest image approved",
    "旧审核已拦截，重新审核后发布",
  ],
  "case.reviewed": ["Opened image", "已查看图片"],
  "case.current": ["Current image", "当前图片"],
  "case.verdict": ["Result", "判定"],
  "case.compare": ["Add the missing comparison", "补上版本比较"],
  "case.end": ["Bring clarity to your next build.", "下一次开发，从看清逻辑开始。"],
  "case.source": ["Example project ↗", "示例项目 ↗"],
  "case.evidence": ["Recordings & tests ↗", "记录与测试 ↗"],
  "case.about": ["About this demo", "演示说明"],
  "case.about.body": [
    "A scripted image-review case with a seeded first-version defect and real execution recordings.",
    "本演示使用图片审核的预设案例、模拟对话与真实运行记录。",
  ],
};

export const chapters = [
  {
    id: "foundation",
    version: 1,
    surface: "codex",
    application: false,
    label: ["Define", "定图"],
    title: ["The flow comes first.", "先定业务，再写代码。"],
    body: [
      "Describe Afterlight, clarify image replacement, then confirm its business graph and states.",
      "描述夜幕的需求，明确替换图片后的处理，在图上确认业务与状态。",
    ],
    dialogue: [
      [
        "user",
        [
          "Build Afterlight: an artist uploads an image; a reviewer opens and approves it for the exhibition.",
          "做一个叫“夜幕”的画展网站。作者上传图片，审核者查看并通过后，图片进入展览。",
        ],
      ],
      [
        "codex",
        [
          "If the artist replaces the image after it was opened, can the previous approval publish the replacement?",
          "审核者查看后，作者又替换了图片，之前的审核能直接发布新图吗？",
        ],
      ],
      [
        "user",
        [
          "No. Replacements need another review. The flow and states match what I want; continue.",
          "不能，换图后要重新审核。业务图和状态符合我的想法，继续开发。",
        ],
      ],
    ],
  },
  {
    id: "build",
    version: 1,
    surface: "codex",
    application: false,
    label: ["Build", "开发"],
    title: ["The graph grows with the code.", "写出的实现，逐层连入图中。"],
    body: [
      "As development progresses, states, API handlers, functions, parameters and tables connect to the business flow.",
      "开发推进时，状态、API、函数、参数与数据表逐步连到业务流中。",
    ],
    dialogue: [
      [
        "user",
        [
          "Build the confirmed flow. Get upload, review and the exhibition running.",
          "按确认的流程开发，先把上传、审核和展览页面跑起来。",
        ],
      ],
      [
        "codex",
        [
          "The pages and API are connected. Expand the graph to see the implementation behind each step.",
          "页面和接口已接通，图中可以展开查看各环节对应的状态、函数、参数和数据表。",
        ],
      ],
    ],
  },
  {
    id: "run",
    version: 1,
    surface: "vibelens",
    label: ["Run", "运行"],
    title: ["One operation. Every change.", "录下一次完整流转。"],
    body: [
      "Start recording in VibeLens, operate Afterlight, then stop and replay. The graph follows the running program.",
      "在 VibeLens 开始记录，再操作夜幕。图随运行变化，结束后可沿时间轴回看。",
    ],
    steps: [
      ["vibelens", ["Start recording.", "点击开始记录。"]],
      [
        "project",
        [
          "Upload blue, open it for review, replace it with orange, then approve the open image.",
          "上传蓝图并打开审核，再换成橙图，通过仍然打开的蓝图。",
        ],
      ],
      [
        "vibelens",
        [
          "Stop recording and replay the changed states and values.",
          "停止记录，回看状态与参数变化。",
        ],
      ],
    ],
  },
  {
    id: "drill",
    version: 1,
    surface: "vibelens",
    label: ["Inspect", "下钻"],
    title: ["Trace the decision to its source.", "沿着运行，找到出错的代码。"],
    body: [
      "Blue was reviewed; orange was published. Follow the publication path to the faulty decision.",
      "审核的是蓝图，展出的却是橙图。沿发布链路下钻，找到出错的判断。",
    ],
    steps: [
      [
        "vibelens",
        [
          "Expand the approval node and compare its recorded inputs.",
          "展开审核节点，对照已查看图片与当前图片的参数。",
        ],
      ],
      [
        "vibelens",
        [
          "Open the bound source: approval_policy() checks the role and omits the image comparison.",
          "打开对应源码：approval_policy() 检查了角色，却遗漏了图片比较。",
        ],
      ],
    ],
  },
  {
    id: "watch",
    version: 1,
    surface: "vibelens",
    label: ["Focus", "关注"],
    title: ["Keep your own signal.", "留下你关心的链路。"],
    body: [
      "Choose the rule, values and effects to watch. Save the view for the next iteration.",
      "选择规则、参数与写入，保存为自己的观察视图。",
    ],
    steps: [
      [
        "vibelens",
        [
          "Keep the approval rule, inputs and database write.",
          "勾选审核规则、输入参数和数据库写入。",
        ],
      ],
      [
        "vibelens",
        [
          "Save this view and replay only the path you are investigating.",
          "保存观察视图，集中回看这条链路。",
        ],
      ],
    ],
  },
  {
    id: "iterate",
    version: 2,
    surface: "codex",
    label: ["Refine", "迭代"],
    title: ["Make the change. Keep the view.", "改动代码，沿用视图。"],
    body: [
      "Add the version check. The same saved path now follows the repaired build.",
      "补上版本检查，用同一条观察链路对照本轮修改。",
    ],
    dialogue: [
      [
        "user",
        [
          "I found the missing image comparison. Fix it: a replaced image must be opened and reviewed again before publication.",
          "我在图中找到了遗漏的图片比较。修复它：换图后必须重新查看和审核，才能发布。",
        ],
      ],
      [
        "codex",
        [
          "The comparison is added to approval_policy(). The graph now follows the changed code, and your saved view is retained.",
          "已在 approval_policy() 中补上比较，图随代码更新，之前保存的观察视图已保留。",
        ],
      ],
    ],
  },
  {
    id: "verify",
    version: 2,
    surface: "vibelens",
    label: ["Verify", "验证"],
    title: ["Watch the repair hold.", "让下一次运行验证修改。"],
    body: [
      "The stale approval stops. A fresh review publishes the intended image.",
      "旧审核被拦截，重新打开最新版后才发布。",
    ],
    steps: [
      [
        "project",
        [
          "Repeat the operation, then reopen the replacement and approve it.",
          "重复刚才的操作，再重新打开新图并通过审核。",
        ],
      ],
      [
        "vibelens",
        [
          "Replay the new recording in your saved view: the old approval stops; the fresh review publishes the intended image.",
          "在原观察视图中回看新记录：旧审核被拦截，重新审核后才发布。",
        ],
      ],
    ],
  },
];
