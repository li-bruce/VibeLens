/** Product explanations share the native graph's display layer IDs and colors. */
export const layerContent = [
  {
    "id": "business",
    "color": 1607275,
    "type": "business",
    "group": ["Intent", "意图"],
    "name": ["Business flow", "业务流程"],
    "question": ["What should people be able to do?", "用户要完成什么？"],
    "body": [
      "Confirm actions and alternative paths in conversation, then follow them into the implementation.",
      "在对话中确认操作与分支，再沿着业务链查看对应实现。",
    ],
    "examples": [
      ["Actors", "Actions", "Outcomes"],
      ["参与者", "业务操作", "业务结果"],
    ],
  },
  {
    "id": "state",
    "color": 9853109,
    "type": "state",
    "group": ["Model", "模型"],
    "name": ["State model", "状态模型"],
    "question": ["What can change, and under which conditions?", "状态如何变化，需要什么条件？"],
    "body": [
      "Define states, events and transitions before coding. Compare the declared path with each actual change.",
      "开发前明确状态、事件与转换条件，运行时对照实际变化。",
    ],
    "examples": [
      ["States", "Events", "Transitions"],
      ["状态", "事件", "转换"],
    ],
  },
  {
    "id": "rules",
    "color": 12286483,
    "type": "decision",
    "group": ["Model", "模型"],
    "name": ["Rule network", "规则网"],
    "question": ["Which facts determine this decision?", "哪些事实决定这次判定？"],
    "body": [
      "Reuse conditions across operations. Inspect their inputs, combinations and actual results.",
      "多个操作共用条件，查看条件的输入、组合和实际判定结果。",
    ],
    "examples": [
      ["Facts", "Conditions", "Decisions"],
      ["输入事实", "条件组合", "判定结果"],
    ],
  },
  {
    "id": "entry",
    "color": 3308985,
    "type": "code-endpoint",
    "group": ["Implementation", "实现"],
    "name": ["Entry points", "入口"],
    "question": ["Where does the request enter?", "请求从哪里进入？"],
    "body": [
      "Find the endpoint and follow its handler into the code.",
      "找到接口，再沿处理函数进入代码。",
    ],
    "examples": [
      ["Routes", "Methods", "Handlers"],
      ["路由", "请求方法", "处理函数"],
    ],
  },
  {
    id: "structure",
    color: 0x6872ad,
    type: "code-file",
    group: ["Implementation", "实现"],
    name: ["Project structure", "工程结构"],
    question: ["Where does the code live?", "代码分布在哪里？"],
    body: ["Explore directories, files and their dependencies.", "查看目录、文件及其依赖。"],
    examples: [
      ["app/", "service.py", "storage.py"],
      ["app/", "service.py", "storage.py"],
    ],
  },
  {
    id: "symbols",
    color: 0xb9654c,
    type: "code-function",
    group: ["Implementation", "实现"],
    name: ["Code execution", "代码执行"],
    question: ["Which call or value explains the result?", "哪个调用或数值解释了结果？"],
    body: [
      "Follow functions, parameters and data access to the source.",
      "沿函数、参数和读写关系，定位源码。",
    ],
    examples: [
      ["Functions", "Parameters", "Calls"],
      ["函数", "参数", "调用"],
    ],
  },
  {
    "id": "data",
    "color": 7444028,
    "type": "store",
    "group": ["Structure", "结构"],
    "name": ["Data structure", "数据结构"],
    "question": ["How is stored data connected?", "存储的数据如何关联？"],
    "body": [
      "Explore tables, collections and fields, connected to the operations that read or change them.",
      "查看表、集合、字段及其关联，连接到实际读写它们的操作。",
    ],
    "examples": [
      ["Tables", "Collections", "Fields"],
      ["表", "集合", "字段"],
    ],
  },
];
