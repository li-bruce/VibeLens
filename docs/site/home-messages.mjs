/** Homepage copy follows one line: the problem, the graph, the next iteration. */
export const messages = {
  "home.kicker": [
    "A Skill for understanding AI-built software",
    "面向 vibe coding 的开发调试 Skill",
  ],
  "home.title": ["AI writes the code\nSee how it works", "看清 AI 写出的程序"],
  "home.lead": [
    "AI changes the code. Keep its logic in view with a state graph—from the flow you confirm to running values and source.",
    "AI 持续改代码，内部逻辑也在变化。用随开发更新的状态网，确认业务、观察运行、定位源码。",
  ],
  "home.demo": ["Follow a real example ↗", "跟随一次完整开发 ↗"],
  "home.speaker": ["You → Codex", "你 → Codex"],
  "home.image.source": [
    "Approval inputs and their function source in VibeLens",
    "VibeLens 中的审核输入与对应函数源码",
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
    "Start with the flow you confirm. Add implementation links while coding, then use recorded behavior to understand and refine it.",
    "先确认你想要的流程，开发时连接对应实现，运行时带着真实的状态和参数回到这张图。",
  ],
  "home.diagram.chat": ["In your coding conversation", "开发对话"],
  "home.diagram.request": [
    "I want to build an online art gallery. Users upload images, and a reviewer decides which ones appear in the exhibition.",
    "我要做一个在线画展应用。用户上传图片后，由审核人决定是否展示在画展页。",
  ],
  "home.diagram.reply": [
    "Let's start with this flow: upload → pending review → approve → exhibit.",
    "我先把流程整理出来：上传图片 → 待审核 → 审核通过 → 展示。",
  ],
  "home.diagram.confirm": ["Confirm the flow and its states", "确认流程与状态"],
  "home.diagram.graph": ["The project's state graph", "项目的状态网"],
  "home.diagram.upload": ["Upload", "上传图片"],
  "home.diagram.review": ["Review", "审核图片"],
  "home.diagram.exhibit": ["Exhibit", "展览展示"],
  "home.diagram.pending": ["Pending", "待审核"],
  "home.diagram.approved": ["Approved", "已通过"],
  "home.diagram.code": ["Code and running values", "实现与运行值"],
  "home.diagram.function": ["approve(image)", "approve(image)"],
  "home.diagram.values": ["actor · image · result", "操作者 · 图片 · 结果"],
  "home.diagram.return": [
    "Inspect the result, then refine the code together",
    "看清问题，再通过对话修改程序",
  ],
  "home.diagram.aria": [
    "A confirmed image-review request connects to business steps, states, a function and its running values, then feeds the next coding conversation",
    "图片审核需求确认后，连接业务步骤、状态、函数和运行值，再支持下一轮开发对话",
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
    "Record a run and follow its decisions, values and source. Describe the issue to AI, then check the next run after the repair.",
    "记录运行，下钻到判断、参数与源码。把问题告诉 AI，修改并检查后，再运行验证。",
  ],
  "home.depth.kicker": ["From overview to implementation", "从全貌到实现"],
  "home.depth.title": ["Follow the part\nyou need to understand", "沿着关心的环节\n逐层看清实现"],
  "home.depth.body": [
    "A business step opens into its states and decisions, then into functions, inputs, API calls, data and source.",
    "从业务环节展开状态与判断，再看到函数、参数、API、数据操作和对应源码。",
  ],
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
