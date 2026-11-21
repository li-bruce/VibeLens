/** A condensed account of the retained Node trial, not a verbatim transcript. */
export const forestCopy = {
  title: ["Build with AI\nUnderstand every change", "用 AI 开发\n看清每一次变化"],
  lead: [
    "I want a team file-sharing app, with private sharing, queued downloads and an independent noticeboard. Follow one project from its first conversation to a changed permission rule.",
    "我要做一个团队文件共享应用：指定同事共享、排队准备下载，再加一个独立公告板。从第一轮对话开始，看清模型、运行和一次权限调整。",
  ],
  business: ["Business", "业务网"],
  states: ["States", "状态网"],
  rules: ["Rules", "规则网"],
  inspection: ["Connected details", "深入关联"],
  networks: ["Choose a network", "选择子网"],
  full: ["Open full recorded graph ↗", "打开完整录制图 ↗"],
  play: ["Play recording", "播放记录"],
  pause: ["Pause recording", "暂停记录"],
  source: ["Open recorded source", "查看对应源码"],
  close: ["Close", "关闭"],
  loading: ["Opening the focused view…", "正在打开局部视图…"],
  retry: ["Retry", "重试"],
  next: ["Continue the conversation", "继续对话"],
  key: [
    "Nodes show actions, states or decisions. Arrows replay recorded state changes. Drag the time control to revisit an event.",
    "节点表示操作、状态或判断；流动箭头回放已记录的状态变化。拖动进度条可回看某个事件。",
  ],
  updated: ["After the change", "调整之后"],
  initial: ["First implementation", "第一版实现"],
  captured: ["Recorded result", "本次记录的结果"],
};

export const forestScenes = [
  {
    id: "foundation",
    title: ["Agree on the behavior", "一起确认业务"],
    body: [
      "AI asks about the choices that change behavior. Files, downloads, announcements and sessions keep their own networks.",
      "AI 追问会改变行为的细节。文件、下载、公告和会话各有自己的网，相关的规则可以共用。",
    ],
    epoch: "initial",
    view: "business",
  },
  {
    id: "build",
    title: ["Connect the model to code", "模型连到实现"],
    body: [
      "After coding, the same concepts lead to actual handlers, permission checks, state values and stored data. Double-click a node to inspect it.",
      "一轮开发后，图中的概念连到实际入口、权限检查、状态值和存储数据。双击节点，查看它对应的实现。",
    ],
    epoch: "initial",
    view: "inspection",
  },
  {
    id: "run",
    title: ["Watch the real sequence", "录下实际发生的顺序"],
    body: [
      "In VibeLens, record while using the app, then stop and replay. This retained run shows the background worker preparing a queued download.",
      "在 VibeLens 开始记录，再操作应用，结束后回放。这里的真实记录展示了后台任务从排队到准备完成。",
    ],
    epoch: "initial",
    view: "states",
    network: "download_task",
    replay: true,
  },
  {
    id: "drill",
    title: ["Find the decision point", "找到决定行为的那一步"],
    body: [
      "The first version checks permission when a task enters the queue. Follow the request to its rule and committed authorization to understand why an accepted task can continue.",
      "初版在任务入队时检查权限。沿请求找到规则和已保存的授权，就能理解为什么已经接受的任务会继续执行。",
    ],
    epoch: "initial",
    view: "inspection",
  },
  {
    id: "iterate",
    title: ["Describe the change to AI", "把调整告诉 AI"],
    body: [
      "Now require a fresh permission check when preparation starts. The updated graph adds cancellation and a shared decision; the other networks retain their identities.",
      "现在要求开始准备时再检查权限。更新后的图加入取消状态和共享判断，其余子网保留原有身份。",
    ],
    epoch: "updated",
    view: "states",
    network: "download_task",
  },
  {
    id: "verify",
    title: ["Inspect the next run", "再看一次运行"],
    body: [
      "The next ordinary run began preparation before access was revoked, so it correctly completed. Check its actual order alongside the separate cancellation test.",
      "这次普通运行在撤销之前已开始准备，因此正常完成。先核对真实顺序，再对照单独验证的排队取消情形。",
    ],
    epoch: "updated",
    view: "states",
    network: "download_task",
    replay: true,
  },
];

export const foundationDialogue = [
  {
    speaker: "You",
    text: [
      "I want a small team file-sharing app and an independent noticeboard. Keep my own application architecture and observe it with VibeLens.",
      "我要做一个小型团队文件共享应用，另有独立公告板。保留项目自己的架构，用 VibeLens 观察。",
    ],
  },
  {
    speaker: "AI",
    text: [
      "Who can share and revoke? What should happen to an accepted download after revocation? Who manages announcements?",
      "谁能共享、撤销？已经接受的下载遇到撤销后怎么办？谁来管理公告？",
    ],
  },
  {
    speaker: "You",
    text: [
      "Only the uploader manages sharing. Accepted downloads continue. Editors manage their own announcements; they do not gain access to other people's files.",
      "上传者管理共享。已接受的下载继续执行。编辑者只管理自己的公告，不因此获得其他人的文件权限。",
    ],
  },
  {
    speaker: "AI",
    text: [
      "Files, downloads and the board are separate capabilities. We also need states for each recipient's access, each task and each announcement. Here are the networks to review.",
      "文件、下载和公告是不同能力。每位接收人的授权、每次任务、每条公告各有状态。先一起看这些网。",
    ],
  },
  {
    speaker: "You",
    text: [
      "That fits. Add real sign-in and sign-out for three test accounts, without registration. An accepted task may be collected again by its original requester.",
      "符合。再加真实登录、退出和三个测试账号，先不做注册。原申请人可以重复领取已接受的任务。",
    ],
  },
  {
    speaker: "AI",
    text: [
      "The session has its own state model. File access remains separate from the editor role. Review Business, States and Rules, then start coding.",
      "会话增加独立状态模型，文件权限仍与编辑者角色分开。查看业务、状态、规则三类图，确认后开始开发。",
    ],
  },
];

export const iterationDialogue = [
  {
    speaker: "You",
    text: [
      "Change the queued case: check the original requester's current access when preparation begins. Cancel a waiting task if access was revoked; a task already preparing may finish.",
      "调整排队的情况：开始准备时检查原申请人当前权限。排队期间被撤销就取消；已经准备中的这一次可以完成。",
    ],
  },
  {
    speaker: "AI",
    text: [
      "I will update the start decision, cancellation state, native checks and mappings together. Restoring access requires a new task; it does not restart the cancelled one.",
      "我会一起更新开始条件、取消状态、原生检查和映射。恢复共享后需要新建任务，已取消任务不会自行重启。",
    ],
  },
];
