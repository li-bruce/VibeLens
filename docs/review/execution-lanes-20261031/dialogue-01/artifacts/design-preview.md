# Business network draft

```mermaid
flowchart LR
  n0["审核通过"]
  n1["确实已分享给当前接收人"]
  n2["等待审核"]
  n3["上传者、指定审核人查看信息或下载"]
  n4["接收人查看信息、下载"]
  n5["指定审核人审核（禁止自审）"]
  n6["上传者选一个接收人并分享"]
  n7["已登录"]
  n8["上传并指定他人审核（已有用户）"]
  n0 -->|"通过后才能分享"| n6
  n7 -->|"访问必须登录"| n4
  n7 -->|"访问必须登录"| n3
  n1 -->|"确实分享给本人"| n4
  n2 -->|"由同事审核"| n5
  n5 -->|"审核通过"| n0
  n6 -->|"指定人员访问"| n4
  n8 -->|"上传后等待审核"| n2
  n8 -->|"审核前即可访问"| n3
  b0["AND · 已登录并具备文件访问权限 (outside scope)"]
  b0 -.->|"Requires"| n3
  b1["AND · 已登录并具备文件访问权限 (outside scope)"]
  b1 -.->|"Requires"| n4
  b2["AND · 已登录、待审核、指定他人审核 (outside scope)"]
  b2 -.->|"Requires"| n5
  b3["AND · 上传者、已通过、选定接收人 (outside scope)"]
  b3 -.->|"Requires"| n6
  b4["AND · 已登录、审核人存在且不是本人 (outside scope)"]
  b4 -.->|"Requires"| n8
  b5["AND · 已登录并具备文件访问权限 (outside scope)"]
  b5 -.->|"Requires"| n3
  b6["AND · 已登录并具备文件访问权限 (outside scope)"]
  b6 -.->|"Requires"| n4
```

[Open the live graph](http://127.0.0.1:62428/graph)

This is a focused view. Dashed boundaries retain original relations; open Web for the complete graph.

Confirm this understanding in the conversation, or describe a correction. Viewing the graph is not confirmation.
