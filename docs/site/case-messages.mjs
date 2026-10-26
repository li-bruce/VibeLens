/** Short product copy; the review material carries the complete case history. */
export const messages = {
  "case.conversation.previous": ["Previous development", "上一次开发对话"],
  "case.dialogue.next": ["Next reply", "继续对话"],
  "case.dialogue.confirm": ["Confirm this flow", "确认这个流程"],
  "case.dialogue.build": ["Start development", "开始开发"],
  "case.app.minimize": ["Collapse application preview", "收起业务窗口"],
  "case.logic": ["Core logic", "核心逻辑"],
  "case.flow.proposed": ["Does this flow match your intent?", "确认这条业务流程"],
  "case.flow.confirmed": ["Flow confirmed", "流程已确认"],
  "case.flow.upload": ["Upload image", "上传图片"],
  "case.flow.pending": ["Pending", "待审核"],
  "case.flow.review": ["Open image", "查看图片"],
  "case.flow.check": ["Same image?", "是否同一张图片"],
  "case.flow.publish": ["Approve", "通过审核"],
  "case.flow.exhibit": ["Exhibition", "进入展览"],
  "case.flow.reopen": ["Replaced: open again", "图片已替换，重新查看"],
  "case.flow.states": ["No image → Pending review → Published", "尚未上传 → 待审核 → 已发布"],
  "case.change": ["Approval: role → role + image match", "审核条件：角色 → 角色与图片一致"],

  "case.home": ["VibeLens", "VibeLens"],
  "case.install": ["Get VibeLens", "开始使用"],
  "case.eyebrow": ["VibeLens in action", "VibeLens 交互演示"],
  "case.title": ["See what your AI built", "看清 AI 写出的程序"],
  "case.lead": [
    "Follow a developer building an image review website: define the flow with VibeLens, record the running program and ask AI to fix a discovered bug.",
    "一位开发者想做图片审核网站：作者上传图片，审核通过后进入展览。跟随这次开发，看 VibeLens 如何确认业务流程、记录运行并验证 AI 的修改。",
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
  "case.conversation": ["Development conversation", "开发对话"],
  "case.location.codex": ["In Codex", "在 Codex 中"],
  "case.location.vibelens": ["In VibeLens", "在 VibeLens 中"],
  "case.location.project": ["In the gallery website", "在画展网站中"],
  "case.user": ["You", "用户"],
  "case.gestures": [
    "Drag to rotate · scroll to zoom · right-drag to pan",
    "拖动旋转 · 滚轮缩放 · 右键拖动平移",
  ],
  "case.app": ["Application replay", "业务界面回放"],
  "case.app.name": ["Gallery website", "画展网站"],
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
  "case.end": ["Bring clarity to your next build", "下一次开发，从看清逻辑开始"],
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
    title: ["The flow comes first", "先定业务，再写代码"],
    body: [
      "Follow the conversation and confirm the proposed flow before development.",
      "逐句明确需求，在对话里的流程图上确认业务与状态。",
    ],
    dialogue: [
      [
        "user",
        [
          "I want a gallery website. An artist uploads images; a reviewer receives a message, opens the image and approves it for the exhibition.",
          "我想做一个画展网站。作者上传图片，审核者收到消息，查看并通过后，图片进入展览。",
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
          "No. Keep the replacement pending until the reviewer opens and approves that image.",
          "不能，替换后仍然待审核，需要重新查看新图再通过。",
        ],
      ],
      [
        "codex",
        [
          "Here is the flow and its states. Does this match the website you want?",
          "我把流程和状态画在这里，看看是否符合你的想法？",
        ],
      ],
      ["user", ["Yes. Build this flow.", "流程正确，按这个开发。"]],
    ],
  },
  {
    id: "build",
    version: 1,
    surface: "codex",
    application: true,
    label: ["Build", "开发"],
    title: ["The graph grows with the code", "写出的实现，逐层连入图中"],
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
    title: ["Follow one complete operation", "录下一次完整流转"],
    body: [
      "Start recording in VibeLens, operate the gallery website, then stop and replay. The graph follows the running program.",
      "在 VibeLens 开始记录，再操作图片审核网站。图随运行变化，结束后可沿时间轴回看。",
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
    title: ["Understand the problem down to its source", "沿着运行，看懂问题出在哪里"],
    body: [
      "Blue was reviewed; orange was published. Inspect the values and source so you can describe the problem to AI.",
      "审核的是蓝图，展出的却是橙图。下钻查看参数和源码，把问题描述给 AI。",
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
    title: ["Keep your own signal", "留下你关心的链路"],
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
    title: ["Describe the issue, let AI make the change", "把问题交给 AI，图随修改更新"],
    body: [
      "Describe the issue and relevant graph values. AI changes the code; your view follows the update.",
      "向 AI 描述现象和图中的关键参数，由 AI 修改代码，观察视图随之更新。",
    ],
    dialogue: [
      [
        "user",
        [
          "I reviewed the blue image but the orange replacement was published. The graph shows reviewed image 1, current image 2, yet the approval returned allowed. Please fix this.",
          "我审核的是蓝图，换成橙图后却直接发布了。图里已查看图片是 1、当前图片是 2，审核仍返回 allowed。请修复这个问题。",
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
    title: ["See the updated logic in action", "看见修改后的业务逻辑"],
    body: [
      "The approval node now checks both role and image identity. Replay the blocked approval, then the successful fresh review.",
      "图中的审核条件增加了图片比较。回看旧审核被拦截、重新查看后发布的两条路径。",
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
