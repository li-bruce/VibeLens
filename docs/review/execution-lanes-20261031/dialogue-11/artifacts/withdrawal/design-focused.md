# Business network draft

```mermaid
flowchart LR
  n0["待指定同事审核"]
  n1["AND · 已登录上传者且仍为待审核 · all"]
  n2["指定同事审核"]
  n3["上传并指定一位同事"]
  n4["上传者撤回待审核文件"]
  n5["已撤回：本次流程结束"]
  n1 -->|"Requires"| n4
  n0 -->|"仅上传者且仍为待审核"| n4
  n3 -->|"上传后交审"| n0
  n0 -->|"只由本次指定的同事审核"| n2
  n4 -->|"撤回后结束；本版不再提交"| n5
  b0["登录 (outside scope)"]
  b0 -.->|"上传入口"| n3
  b1["审核通过 (outside scope)"]
  n2 -.->|"通过"| b1
  b2["未通过：流程结束 (outside scope)"]
  n2 -.->|"未通过即结束，不重提"| b2
  b3["指定审核人不能是自己 (outside scope)"]
  b3 -.->|"从已有用户中选择一位其他同事"| n3
  b4["查看信息或下载 (outside scope)"]
  n5 -.->|"保留文件；仅上传者可读取"| b4
  b5["Rules (outside scope)"]
  b5 -.->|"Rule expression"| n1
  b6["已登录 (outside scope)"]
  b6 -.->|"all"| n1
  b7["当前用户是上传者 (outside scope)"]
  b7 -.->|"all"| n1
  b8["仍为待审核 (outside scope)"]
  b8 -.->|"all"| n1
  b9["AND · 仅指定审核人可审核 (outside scope)"]
  b9 -.->|"Requires"| n2
  b10["AND · 登录且选择一位已有的其他同事 (outside scope)"]
  b10 -.->|"Requires"| n3
```

[Open the live graph](http://127.0.0.1:8985/graph)

This is a focused view. Dashed boundaries retain original relations; open Web for the complete graph.

Confirm this understanding in the conversation, or describe a correction. Viewing the graph is not confirmation.
