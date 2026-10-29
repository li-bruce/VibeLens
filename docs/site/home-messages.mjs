/** Homepage copy follows one line: the problem, the graph, the next iteration. */
export const messages = {
  "home.kicker": [
    "A Skill for understanding AI-built software",
    "面向 vibe coding 的开发调试 Skill",
  ],
  "home.title": ["AI writes the code\nSee how it works", "看清 AI 写出的程序"],
  "home.lead": [
    "Follow AI-built software from the flow you confirm to running values and source.",
    "用随开发更新的状态网，确认业务、观察运行、定位源码。",
  ],
  "home.demo": ["Follow a real example ↗", "跟随一次完整开发 ↗"],
  "home.speaker": ["You → Codex", "你 → Codex"],
  "home.image.source": [
    "A sharing state and the function that changes it in VibeLens",
    "VibeLens 中的共享状态与对应函数源码",
  ],
  "home.image.layers": [
    "Business, decision and parameter relationships in VibeLens 3D",
    "VibeLens 三维视图中的业务、判断与参数关系",
  ],
  "home.image.caption": [
    "One operation, from its inputs to the function that handled it",
    "从一次操作的输入，看到负责处理的函数",
  ],
  "home.problem.kicker": ["The challenge of vibe coding", "Vibe coding 中的困惑"],
  "home.problem.title": [
    "The app works\nHow did it reach that result?",
    "功能做出来了\n内部逻辑看清了吗",
  ],
  "home.problem.body": [
    "AI keeps changing the code. A working screen tells you little about the conditions it checked, the state it changed or the data it wrote.",
    "AI 一轮轮修改代码，界面上能看到结果，却很难看清它检查了什么条件、改变了哪些状态、把数据写到了哪里。",
  ],
  "home.workflow.kicker": ["The approach", "VibeLens 的思路"],
  "home.workflow.title": [
    "Connect the intent,\nthe code and the run",
    "把需求、代码和运行\n连成一张状态网",
  ],
  "home.workflow.body": [
    "Confirm the flow, follow its implementation, then record a run to see what happened.",
    "先看图确认流程，开发时连接实现，运行时查看状态与参数。",
  ],
  "home.diagram.chat": ["In your coding conversation", "开发对话"],
  "home.diagram.request": [
    "I want a file-sharing app. Users log in, upload files and share them with specific people. Recipients can download while sharing is active.",
    "我要做一个文件共享应用。用户登录后上传文件，共享给指定的人，对方可以查看和下载；取消共享后就不能再下载。",
  ],
  "home.diagram.reply": [
    "Upload → share → download. The owner controls sharing; each download checks the current permission.",
    "上传 → 共享 → 下载。所有者决定共享给谁，每次下载都检查当前权限。",
  ],
  "home.diagram.confirm": ["Confirm the flow and its states", "确认流程与状态"],
  "home.diagram.graph": ["The project's state graph", "项目的状态网"],
  "home.diagram.upload": ["Upload", "上传文件"],
  "home.diagram.share": ["Share", "指定接收者"],
  "home.diagram.download": ["Download", "下载文件"],
  "home.diagram.shared": ["Shared", "共享中"],
  "home.diagram.revoked": ["Revoked", "已取消"],
  "home.diagram.code": ["Code and running values", "实现与运行值"],
  "home.diagram.function": ["can_download(…)", "can_download(…)"],
  "home.diagram.values": ["actor · grant · result", "用户 · 授权 · 结果"],
  "home.diagram.return": [
    "Inspect the result, then refine the code together",
    "看清问题，再通过对话修改程序",
  ],
  "home.diagram.aria": [
    "A file-sharing request connects to business steps, sharing states, permission checks and source, then feeds the next coding conversation",
    "文件共享需求连接业务流程、共享状态、权限判断和源码，再支持下一轮开发对话",
  ],
  "home.step.confirm": ["Agree on the behavior", "先确认要做什么"],
  "home.step.confirm.body": [
    "VibeLens clarifies your description and shows the first flow for you to confirm.",
    "通过必要的提问澄清描述，在对话里看图确认业务流程和状态。",
  ],
  "home.step.build": ["Keep the graph in step with your code", "代码更新，图也更新"],
  "home.step.build.body": [
    "As AI changes the project, the graph follows its functions, parameters, API and data relationships.",
    "每次 AI 迭代项目，图中的函数、参数、API 和数据关系也会更新。",
  ],
  "home.step.inspect": ["Find and verify the next change", "看清问题，再验证修改"],
  "home.step.inspect.body": [
    "Record a run, find the cause, then ask AI to repair it and verify the result.",
    "记录运行，下钻定位原因，让 AI 修改后再验证。",
  ],
  "home.depth.kicker": ["From overview to implementation", "从全貌到实现"],
  "home.depth.title": ["From your idea\nto its implementation", "从业务想法\n一路看到具体实现"],
  "home.depth.body": [
    "Explore one connected graph, from the flow you confirm to its states, decisions, running values and source.",
    "一张相互连接的网，从对话中确认的业务流程，逐层深入状态、判定、运行值与源码。",
  ],
  "home.depth.try": ["Follow a path ↗", "跟随一条链路 ↗"],
  "home.depth.overview": ["Business flow", "业务流程"],
  "home.depth.overview.body": ["Where did the operation go?", "操作走到了哪一步"],
  "home.depth.logic": ["States and decisions", "状态与判断"],
  "home.depth.logic.body": ["Which condition decided the result?", "什么条件决定了结果"],
  "home.depth.code": ["Functions, data and source", "函数、数据与源码"],
  "home.depth.code.body": ["What handled these values?", "这些值由哪段实现处理"],
  "home.depth.caption": ["Input values and their source", "输入参数与对应源码"],
  "home.modes.title": [
    "Build with the graph\nor observe your own design",
    "从状态网开发\n也能观察已有设计",
  ],
  "home.modes.drive": ["Drive", "驱动模式"],
  "home.modes.drive.body": [
    "Use the confirmed states and transitions to structure execution.",
    "以确认的状态与转换组织程序执行。",
  ],
  "home.modes.observe": ["Observe", "观察模式"],
  "home.modes.observe.body": [
    "Keep your existing design and explore its internal flow and runtime state.",
    "沿用现有设计，查看内部流程和运行状态。",
  ],
  "home.controls.title": ["Ask for the path\nyou want to see", "说出你关心的链路"],
  "home.controls.body": [
    "Describe the path you want to follow. VibeLens brings it into focus.",
    "说出想观察的业务链路，VibeLens 会整理出对应视图。",
  ],
  "home.controls.more": [
    "Try view controls and replay filtering ↗",
    "在演示中体验视图控制与回放筛选 ↗",
  ],
};
