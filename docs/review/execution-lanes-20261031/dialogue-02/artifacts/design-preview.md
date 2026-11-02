# Business network draft

```mermaid
flowchart LR
  n0["查看信息或下载"]
  n1["审核通过"]
  n2["指定审核人不能是自己"]
  n3["唯一指定接收人"]
  n4["待指定同事审核"]
  n5["指定同事审核"]
  n6["未通过：流程结束"]
  n7["上传者分享给一个接收人"]
  n8["登录"]
  n9["上传并指定一位同事"]
  n10["上传者和审核人始终可读取"]
  n7 -->|"指定一个已有账号"| n3
  n1 -->|"仅通过后由上传者分享"| n7
  n8 -->|"访问必须已登录"| n0
  n3 -->|"通过且已分享给本人"| n0
  n2 -->|"从已有用户中选择一位其他同事"| n9
  n10 -->|"审核前后均可读取"| n0
  n8 -->|"上传入口"| n9
  n5 -->|"通过"| n1
  n5 -->|"未通过即结束，不重提"| n6
  n9 -->|"上传后交审"| n4
  n4 -->|"只由本次指定的同事审核"| n5
  b0["AND · 登录并具备读取资格 (outside scope)"]
  b0 -.->|"Requires"| n0
  b1["AND · 仅指定审核人可审核 (outside scope)"]
  b1 -.->|"Requires"| n5
  b2["AND · 登录且通过审核且为上传者 (outside scope)"]
  b2 -.->|"Requires"| n7
  b3["AND · 登录且选择一位已有的其他同事 (outside scope)"]
  b3 -.->|"Requires"| n9
```

[Open the live graph](http://127.0.0.1:8973/graph)

This is a focused view. Dashed boundaries retain original relations; open Web for the complete graph.

Still to confirm:

- 这版业务图是否符合你的意思？确认后我再开始实现。

Confirm this understanding in the conversation, or describe a correction. Viewing the graph is not confirmation.
