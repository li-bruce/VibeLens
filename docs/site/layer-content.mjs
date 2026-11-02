/** Product explanations use the same layer IDs as the native graph. */
export const layerContent = [
  {
    id: "business",
    color: 0x18866b,
    type: "business",
    group: ["Intent", "意图"],
    name: ["Business flow", "业务流程"],
    question: ["What should the application do?", "这个应用要完成什么？"],
    body: [
      "The actions and paths you confirm in conversation become the starting graph.",
      "把对话中确认的操作与流转关系，变成开发的起点。",
    ],
    examples: [
      ["Upload", "Share", "Download"],
      ["上传", "共享", "下载"],
    ],
  },
  {
    id: "state",
    color: 0x9658b5,
    type: "state",
    group: ["Model", "模型"],
    name: ["States", "状态"],
    question: ["What can change, and when?", "状态何时发生变化？"],
    body: [
      "States, transitions, waiting and parallel activity connect the declared behavior to its actual execution.",
      "查看状态、转换、等待与并行过程，对照程序实际执行的路径。",
    ],
    examples: [
      ["Private", "Shared", "Private"],
      ["私有", "已共享", "私有"],
    ],
  },
  {
    id: "rules",
    color: 0xbb7a13,
    type: "decision",
    group: ["Model", "模型"],
    name: ["Rules", "规则"],
    question: ["Which condition decided the result?", "什么条件决定了结果？"],
    body: [
      "Shared conditions form a rule network. Follow a decision to its inputs and the function that checked them.",
      "共用条件组成规则网，从判定结果追到输入事实和执行检查的函数。",
    ],
    examples: [
      ["Signed in", "Owner", "Recipient"],
      ["已登录", "所有者", "接收者"],
    ],
  },
  {
    id: "api",
    color: 0xc15463,
    type: "code-endpoint",
    group: ["Implementation", "实现"],
    name: ["API", "API 接口"],
    question: ["Where did the request enter?", "请求从哪里进入程序？"],
    body: [
      "Routes and handlers connect a request to the business operation and its implementation.",
      "路由和处理函数，把一次请求连接到业务操作与对应实现。",
    ],
    examples: [
      ["POST /files", "POST /share", "GET /download"],
      ["POST /files", "POST /share", "GET /download"],
    ],
  },
  {
    id: "execution",
    color: 0x327db9,
    type: "function",
    group: ["Implementation", "实现"],
    name: ["Functions & values", "核心函数与值"],
    question: ["Which values did the function use?", "函数使用了哪些值？"],
    body: [
      "Key functions, parameters and observed values show how an operation reached its result.",
      "关键函数、参数与运行值，让一次操作的内部处理过程清晰可见。",
    ],
    examples: [
      ["share()", "file_id", "recipient_id"],
      ["share()", "file_id", "recipient_id"],
    ],
  },
  {
    id: "operations",
    color: 0x008f98,
    type: "query",
    group: ["Implementation", "实现"],
    name: ["Data operations", "数据处理"],
    question: ["What was read, changed or committed?", "读取、处理和写入了什么？"],
    body: [
      "Queries, transformations and transactions reveal the data path and its recorded results.",
      "沿着查询、转换与事务，核对数据流转和记录中的实际结果。",
    ],
    examples: [
      ["Read grants", "Update access", "Commit"],
      ["读取授权", "更新权限", "提交事务"],
    ],
  },
  {
    id: "project",
    color: 0x8f7047,
    type: "code-directory",
    group: ["Structure", "结构"],
    name: ["Project structure", "工程结构"],
    question: ["Where does each responsibility live?", "功能分布在哪些文件中？"],
    body: [
      "Scanned directories, files and imports reveal module boundaries, dependencies and cycles.",
      "自动扫描目录、文件和导入关系，查看模块分工、依赖与循环。",
    ],
    examples: [
      ["app/", "service.py", "storage.py"],
      ["app/", "service.py", "storage.py"],
    ],
  },
  {
    id: "code",
    color: 0x6566bd,
    type: "code-function",
    group: ["Structure", "结构"],
    name: ["Code symbols", "代码功能"],
    question: ["Which code implements this part?", "这部分由哪些代码实现？"],
    body: [
      "Static declarations, calls and parameters complete the path to the source file. Open local detail as needed.",
      "继续下钻到静态声明、调用与参数，按需展开局部代码并查看源码。",
    ],
    examples: [
      ["SharingService", "share()", "parameters"],
      ["SharingService", "share()", "参数"],
    ],
  },
  {
    id: "data",
    color: 0x71963c,
    type: "store",
    group: ["Structure", "结构"],
    name: ["Data structure", "数据结构"],
    question: ["How is the data connected?", "数据之间如何关联？"],
    body: [
      "Tables, collections, fields and relationships connect storage structure to the code that uses it.",
      "表、集合、字段与关联关系，连接到使用它们的查询和函数。",
    ],
    examples: [
      ["users", "files", "shares"],
      ["users", "files", "shares"],
    ],
  },
];

const order = [
  "business",
  "state",
  "rules",
  "api",
  "execution",
  "project",
  "code",
  "operations",
  "data",
];
layerContent.sort((a, b) => order.indexOf(a.id) - order.indexOf(b.id));
