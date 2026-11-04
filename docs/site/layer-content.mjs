/** Product explanations share the native graph concern IDs and colors. */
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
      ["Upload", "Share", "Download"],
      ["上传", "共享", "下载"],
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
      ["Private", "Shared", "Revoked"],
      ["私有", "已共享", "已撤销"],
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
      ["Signed in", "Owner", "Active grant"],
      ["已登录", "所有者", "有效授权"],
    ],
  },
  {
    "id": "implementation",
    "color": 3308985,
    "type": "code-function",
    "group": ["Implementation", "实现"],
    "name": ["Implementation", "程序实现"],
    "question": ["Which code handles this operation?", "哪些代码完成这次操作？"],
    "body": [
      "Move through API entries, files, functions and selected values. Open local calls and data access when needed.",
      "从接口、文件深入函数与关键值，按需展开局部调用和数据访问。",
    ],
    "examples": [
      ["POST /share", "service.py", "share()"],
      ["POST /share", "service.py", "share()"],
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
      ["users", "files", "shares"],
      ["users", "files", "shares"],
    ],
  },
];
