# Business network draft

```mermaid
flowchart LR
  n0["查看信息或下载"]
  n1["唯一指定接收人"]
  n2["已保存的拒绝原因"]
  n3["指定同事审核"]
  n4["不通过需填写原因；通过可空"]
  n5["登录"]
  n2 -->|"上传者在详情查看原因"| n0
  n3 -->|"拒绝时保存原因"| n2
  n5 -->|"访问必须已登录"| n0
  n1 -->|"通过且已分享给本人"| n0
  n4 -->|"拒绝必填；通过无需填写"| n3
  b0["上传者分享给一个接收人 (outside scope)"]
  b0 -.->|"指定一个已有账号"| n1
  b1["上传并指定一位同事 (outside scope)"]
  n5 -.->|"上传入口"| b1
  b2["审核通过 (outside scope)"]
  n3 -.->|"通过"| b2
  b3["未通过：流程结束 (outside scope)"]
  n3 -.->|"未通过即结束，不重提"| b3
  b4["待指定同事审核 (outside scope)"]
  b4 -.->|"只由本次指定的同事审核"| n3
  b5["上传者始终可读；审核人撤回后不可读 (outside scope)"]
  b5 -.->|"上传者始终可读；审核人仅未撤回时可读"| n0
  b6["已撤回：本次流程结束 (outside scope)"]
  b6 -.->|"保留文件；仅上传者可读取"| n0
  b7["AND · 登录并具备读取资格 (outside scope)"]
  b7 -.->|"Requires"| n0
  b8["AND · 仅指定审核人可审核 (outside scope)"]
  b8 -.->|"Requires"| n3
```

[Open the live graph](http://127.0.0.1:8986/graph)

This is a focused view. Dashed boundaries retain original relations; open Web for the complete graph.

Still to confirm:

- 拒绝时原因必填并保存，上传者在详情看到原文；通过时无需填写，现有审核与读取权限保持。业务图将按这条分支更新，这样理解是否正确？

Confirm this understanding in the conversation, or describe a correction. Viewing the graph is not confirmation.
