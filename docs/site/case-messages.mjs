/** Short product copy; the review material carries the complete case history. */
export const messages = {
  "case.home": ["VibeLens", "VibeLens"],
  "case.install": ["Get VibeLens", "开始使用"],
  "case.eyebrow": ["VibeLens in action", "VibeLens 交互演示"],
  "case.title": ["See what your AI built.", "看清 AI 写出的程序。"],
  "case.lead": [
    "Start with the business. Follow the logic. Refine every iteration.",
    "从业务定图，沿运行下钻，让每轮迭代有据可循。",
  ],
  "case.scroll": ["Scroll to follow the build", "向下，跟随一次开发"],
  "case.nav": ["Development stages", "开发阶段"],
  "case.confirm": ["Confirm the flow", "确认业务图"],
  "case.states": ["See the states", "查看状态机"],
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
  "case.layered": ["All layers", "全部图层"],
  "case.paused": ["Play", "播放"],
  "case.pause": ["Pause", "暂停"],
  "case.position": ["Playback", "回放进度"],
  "case.conversation": ["Example conversation", "示例对话"],
  "case.user": ["You", "用户"],
  "case.gestures": [
    "Drag to rotate · scroll to zoom · right-drag to pan",
    "拖动旋转 · 滚轮缩放 · 右键拖动平移",
  ],
  "case.app": ["Application replay", "业务界面回放"],
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
  "case.check.fail": [
    "Only the role was checked. The opened image was ignored.",
    "这里只检查了角色，遗漏了审核对象的校验。",
  ],
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
    label: ["Define", "定图"],
    title: ["The flow comes first.", "先定业务，再写代码。"],
    body: [
      "Confirm the business and state graph before development begins.",
      "在对话中确认业务与状态，让后续开发有清晰的地基。",
    ],
    dialogue: [
      [
        "user",
        [
          "Build a gallery: an artist uploads an image, a reviewer opens and approves it, then it appears in the exhibition.",
          "做一个画展网站：作者上传图片，审核者查看并通过后，图片进入展览。",
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
          "No. Open the replacement and review it again. This flow looks right; continue.",
          "不能，需要查看新图后重新审核。这个业务图符合我的想法，继续开发。",
        ],
      ],
    ],
  },
  {
    id: "run",
    label: ["Run", "运行"],
    title: ["One operation. Every change.", "录下一次完整流转。"],
    body: [
      "Upload, open, replace, approve. Follow the recorded run.",
      "上传、查看、替换、审核。看见每一步如何影响结果。",
    ],
    dialogue: [
      [
        "user",
        [
          "Record this: upload the blue image, open it for review, replace it with orange, then approve the image still open.",
          "录一下：上传蓝图、打开审核、替换成橙图，再通过仍然打开的蓝图。",
        ],
      ],
      [
        "codex",
        [
          "The operation is recorded. Replay it to follow the inputs, decisions and publication.",
          "操作已记录，可以沿业务流回放，查看参数、判断和发布结果。",
        ],
      ],
    ],
  },
  {
    id: "drill",
    label: ["Inspect", "下钻"],
    title: ["Trace the decision to its source.", "沿着运行，找到出错的代码。"],
    body: [
      "An unseen image was published. Follow the approval rule into approval_policy().",
      "程序发布了未确认的图片。沿审核节点下钻，查看 approval_policy() 的判断条件。",
    ],
    dialogue: [
      [
        "user",
        [
          "I approved blue. Why did orange appear? Open the approval logic.",
          "我审核的是蓝图，怎么展出橙图了？展开审核逻辑看看。",
        ],
      ],
      [
        "codex",
        [
          "approval_policy() only checks the role. It receives both image versions but never compares them.",
          "approval_policy() 只检查了角色，虽然收到两张图片的版本参数，却没有比较它们。",
        ],
      ],
    ],
  },
  {
    id: "watch",
    label: ["Focus", "关注"],
    title: ["Keep your own signal.", "留下你关心的链路。"],
    body: [
      "Choose the rule, values and effects to watch. Save the view for the next iteration.",
      "选择规则、参数与写入，保存为自己的观察视图。",
    ],
    dialogue: [
      [
        "user",
        [
          "Keep the approval rule, its inputs and the database write. Save this as My approval path.",
          "只保留审核规则、输入参数和数据库写入，保存成“我的审核链路”。",
        ],
      ],
      [
        "codex",
        [
          "Choose the elements below and save the view. This path will remain available after the code changes.",
          "可以在下方选择保留内容并保存，下次代码更新后继续沿这条链路观察。",
        ],
      ],
    ],
  },
  {
    id: "iterate",
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
          "Compare the opened image with the current image before publishing. If they differ, ask the reviewer to reopen it.",
          "发布前比较已查看的图片和当前图片，不一致就要求审核者重新打开图片。",
        ],
      ],
      [
        "codex",
        [
          "The comparison is added to approval_policy(). The saved view now points to the updated code.",
          "已在 approval_policy() 中补上比较，保存的观察视图也已对应到新代码。",
        ],
      ],
    ],
  },
  {
    id: "verify",
    label: ["Verify", "验证"],
    title: ["Watch the repair hold.", "让下一次运行验证修改。"],
    body: [
      "The stale approval stops. A fresh review publishes the intended image.",
      "旧审核被拦截，重新打开最新版后才发布。",
    ],
    dialogue: [
      [
        "user",
        [
          "Repeat the same operation, then reopen the latest image and approve it.",
          "重复刚才的操作，再重新打开最新图片并通过审核。",
        ],
      ],
      [
        "codex",
        [
          "The old approval is rejected. Opening and approving the latest image publishes that exact image. The check passes.",
          "旧审核已被拦截，重新查看并审核后发布的是同一张图片，复测通过。",
        ],
      ],
    ],
  },
];
