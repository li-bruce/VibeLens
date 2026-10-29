# Business network draft

```mermaid
flowchart LR
  n0["下载文件"]
  n1["私有文件"]
  n2["用户登录"]
  n3["上传者成为所有者"]
  n4["指定接收者"]
  n5["所有者指定接收者"]
  n6["上传自己的文件"]
  n7["查看文件"]
  n3 -->|"所有者可下载（待确认）"| n0
  n3 -->|"拥有"| n1
  n3 -->|"仅所有者可共享（待确认）"| n5
  n3 -->|"所有者可查看（待确认）"| n7
  n4 -->|"获共享后下载"| n0
  n4 -->|"获共享后查看（含义待确认）"| n7
  n5 -->|"授予访问权"| n4
  n6 -->|"确定所有者"| n3
  n1 -->|"选择文件共享"| n5
  n2 -->|"登录后上传"| n6
  b0["已登录且有访问权 (outside scope)"]
  b0 -.->|"Requires"| n0
  b1["已登录且为所有者（共享权限待确认） (outside scope)"]
  b1 -.->|"Requires"| n5
  b2["已登录 (outside scope)"]
  b2 -.->|"Requires"| n6
  b3["已登录且有访问权 (outside scope)"]
  b3 -.->|"Requires"| n7
```

[Open the live graph](http://127.0.0.1:8847/graph)

This is a focused view. Dashed boundaries retain original relations; open Web for the complete graph.

Still to confirm:

- 项目采用 drive（状态声明驱动执行）还是 observe（应用自己执行，图负责观察）？
- 初版账号使用预置测试账号，还是提供自行注册？
- 请确认：仅所有者能共享；所有者和指定接收者能查看、下载；其他人无权访问。“查看”是文件信息还是也需要在线预览内容？

Confirm this understanding in the conversation, or describe a correction. Viewing the graph is not confirmation.
