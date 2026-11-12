/** Product copy: intent, implementation and execution, in the user's language. */
export const messages = {
  "nav.explore": ["Explore", "功能"],
  "nav.demo": ["Demo", "交互演示"],
  "home.kicker": ["A Skill for vibe coding", "辅助理解与调试的 Vibe Coding Skill"],
  "home.title": ["See the logic\nbehind your code", "看懂 AI\n写出的程序"],
  "home.lead": [
    "Build a shared model with AI. Follow its rules, state changes and calls into the running code.",
    "与 AI 一起确认业务、状态和规则，再沿图看清程序如何运行。",
  ],
  "home.demo": ["Try the interactive demo ↗", "体验交互演示 ↗"],
  "hero.start": ["Get VibeLens", "开始使用"],
  "home.dimensions": ["View dimensions", "视图维度"],
  "home.proof.path": [
    "One operation. Its values. The exact source.",
    "从一次操作，找到关键值和对应源码",
  ],
  "home.proof.open": ["Explore the path ↗", "探索这条链路 ↗"],
  "home.image.source": [
    "A focused execution path, captured values and highlighted source",
    "聚焦后的执行链路、采集数值与高亮源码",
  ],
  "home.image.layers": [
    "The connected graph in a three-dimensional view",
    "三维视图中相互连接的图层",
  ],
  "home.problem.kicker": ["As your project grows", "代码在变，理解也要跟上"],
  "home.problem.title": ["Working code\nYou can understand", "功能做出来了\n内部发生了什么"],
  "home.problem.body": [
    "AI can change several parts at once. VibeLens connects the intended behavior to the implementation, so you can see what changed and trace an unexpected result.",
    "AI 一轮修改可能涉及多处代码。VibeLens 把业务含义和实现连起来，让你看清变化，追查意外结果。",
  ],
  "home.step.confirm": ["Agree on the model", "先确认模型"],
  "home.step.confirm.body": [
    "Clarify the flow, states and shared rules. Review the graph before coding.",
    "澄清流程、状态和共用规则，开发前看图确认。",
  ],
  "home.step.confirm.link": ["See the first conversation ↗", "看第一轮对话 ↗"],
  "home.step.inspect": ["Follow a real run", "再观察运行"],
  "home.step.inspect.body": [
    "Record an operation. Follow its calls and values down to the source.",
    "录下一次操作，沿调用与数值逐层深入源码。",
  ],
  "home.step.inspect.link": ["Inspect the recording ↗", "查看运行记录 ↗"],
  "home.step.refine": ["Make the next change", "带着发现迭代"],
  "home.step.refine.body": [
    "Describe the finding to AI. Code, mappings and checks evolve together.",
    "把发现交给 AI，代码、映射和检查随每轮开发一起更新。",
  ],
  "home.step.refine.link": ["Follow the repair ↗", "跟随一次修改 ↗"],
  "home.depth.kicker": ["One graph, different depths", "同一张图，逐层深入"],
  "home.depth.title": [
    "Start with intent\nArrive at the exact value",
    "从你想做什么\n到代码如何做到",
  ],
  "home.depth.body": [
    "Follow cross-layer links from a business action to its rules, states, functions and data. Expand only the part you want to understand.",
    "沿跨层关系，从业务操作追到规则、状态、函数和数据。逐层展开当前关心的部分。",
  ],
  "home.depth.try": ["Explore a connected path ↗", "探索一条完整链路 ↗"],
  "home.modes.kicker": ["Your architecture, your choice", "两种开发方式"],
  "home.modes.title": [
    "A model to build with\nA lens to look through",
    "用状态图驱动开发\n或观察自己的实现",
  ],
  "home.modes.drive": ["Drive", "驱动"],
  "home.modes.drive.body": [
    "Build execution around the confirmed state model.",
    "让程序基于确认后的状态模型执行。",
  ],
  "home.modes.observe": ["Observe", "观察"],
  "home.modes.observe.body": [
    "Map your existing logic and follow its real behavior.",
    "沿用自己的架构，映射并观察实际行为。",
  ],
  "home.case.kicker": ["Your investigation workspace", "你的观察工作台"],
  "home.case.title": ["A clear path\nThrough a complex system", "复杂的项目\n清楚的观察链路"],
  "home.case.body": [
    "Choose a view yourself, or describe it in conversation. Keep the relevant nodes, then watch their values and lifetimes together.",
    "手动选择，或在对话中描述观察范围。保留相关节点，一起查看数值变化与执行周期。",
  ],
  "home.tools.focus": ["Your own view", "自定义视图"],
  "home.tools.focus.body": [
    "Choose layers and relations. Keep your layout across iterations.",
    "选择图层与关系，迭代后保留你的布局。",
  ],
  "home.tools.record": ["One recording", "录制与回放"],
  "home.tools.record.body": [
    "Capture an operation and scrub its timeline.",
    "录下一次操作，拖动时间轴查看过程。",
  ],
  "home.tools.trace": ["Connected details", "逐层定位"],
  "home.tools.trace.body": [
    "Switch between source names and semantic labels. Inspect a node, then open its source.",
    "切换源码名与语义名，查看节点含义，再打开对应源码。",
  ],
  "home.focus.prompt": [
    "/vibelens Show this operation's states, rules and key values. Save it as my inspection view.",
    "/vibelens 只看这次操作的状态、规则和关键参数，保存为我的观察视图。",
  ],
  "home.focus.caption": ["Choose the scope. Follow the changes.", "选好范围，跟随变化"],
  "install.kicker": ["For your next project", "从你的项目开始"],
  "install.title": ["Start with a conversation", "从一句需求开始"],
  "install.body": [
    "Install the Skill, then call $vibelens in Codex.",
    "安装 Skill 后，在 Codex 中使用 $vibelens。",
  ],
  "install.prompt": [
    "$vibelens\nHelp me map this project's flow, states and rules. Show me the graph before we start coding.",
    "$vibelens\n先帮我梳理这个项目的业务流程、状态和规则，看图确认后再开始开发。",
  ],
  "install.copy": ["Copy prompt", "复制提示词"],
  "install.guide": ["Installation & usage ↗", "安装与使用 ↗"],
};
