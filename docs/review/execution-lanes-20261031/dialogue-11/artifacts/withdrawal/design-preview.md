# Business network draft

```mermaid
flowchart LR
  n0["查看信息或下载"]
  n1["审核通过"]
  n2["唯一指定接收人"]
  n3["待指定同事审核"]
  n4["AND · 登录并具备读取资格 · all"]
  n5["AND · 仅指定审核人可审核 · all"]
  n6["指定同事审核"]
  n7["登录"]
  n8["上传并指定一位同事"]
  n9["上传者始终可读；审核人撤回后不可读"]
  n10["上传者撤回待审核文件"]
  n11["已撤回：本次流程结束"]
  n7 -->|"访问必须已登录"| n0
  n2 -->|"通过且已分享给本人"| n0
  n9 -->|"上传者始终可读；审核人仅未撤回时可读"| n0
  n11 -->|"保留文件；仅上传者可读取"| n0
  n4 -->|"Requires"| n0
  n5 -->|"Requires"| n6
  n7 -->|"上传入口"| n8
  n3 -->|"仅上传者且仍为待审核"| n10
  n6 -->|"通过"| n1
  n8 -->|"上传后交审"| n3
  n3 -->|"只由本次指定的同事审核"| n6
  n10 -->|"撤回后结束；本版不再提交"| n11
  b0["上传者分享给一个接收人 (outside scope)"]
  b0 -.->|"指定一个已有账号"| n2
  b1["未通过：流程结束 (outside scope)"]
  n6 -.->|"未通过即结束，不重提"| b1
  b2["上传者分享给一个接收人 (outside scope)"]
  n1 -.->|"仅通过后由上传者分享"| b2
  b3["指定审核人不能是自己 (outside scope)"]
  b3 -.->|"从已有用户中选择一位其他同事"| n8
  b4["Rules (outside scope)"]
  b4 -.->|"Rule expression"| n4
  b5["Rules (outside scope)"]
  b5 -.->|"Rule expression"| n5
  b6["已登录 (outside scope)"]
  b6 -.->|"all"| n4
  b7["OR · 上传者、审核人或满足条件的接收人 (outside scope)"]
  b7 -.->|"all"| n4
  b8["已登录 (outside scope)"]
  b8 -.->|"all"| n5
  b9["当前用户是指定审核人 (outside scope)"]
  b9 -.->|"all"| n5
  b10["AND · 登录且选择一位已有的其他同事 (outside scope)"]
  b10 -.->|"Requires"| n8
  b11["AND · 已登录上传者且仍为待审核 (outside scope)"]
  b11 -.->|"Requires"| n10
```

[Open the live graph](http://127.0.0.1:8985/graph)

This is a focused view. Dashed boundaries retain original relations; open Web for the complete graph.

Confirm this understanding in the conversation, or describe a correction. Viewing the graph is not confirmation.
