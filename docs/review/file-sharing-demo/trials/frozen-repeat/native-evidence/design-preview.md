# Business network draft

```mermaid
flowchart LR
  n0["该文件不可见，下载被拒绝"]
  n1["所有者选择已有用户（示例：许宁）"]
  n2["接收者下载文件"]
  n3["用户登录"]
  n4["上传者成为所有者（示例：林舟）"]
  n5["接收者查看文件名、大小、共享人"]
  n6["共享文件（仅所有者可操作）"]
  n7["周岚：未收到该文件的共享"]
  n8["上传自己的文件"]
  n6 -->|"建立所有者与接收者关系"| n5
  n7 -->|"无该文件共享权限"| n0
  n8 -->|"上传确定所有权"| n4
  n5 -->|"点击下载"| n2
  n3 -->|"登录后"| n8
  n4 -->|"选择接收者"| n1
  n1 -->|"一次选择一个已有用户"| n6
  b0["AND · 已登录且为所有者或接收者 (outside scope)"]
  b0 -.->|"Requires"| n2
  b1["AND · 已登录、是所有者且接收者存在 (outside scope)"]
  b1 -.->|"Requires"| n6
  b2["已登录 (outside scope)"]
  b2 -.->|"Requires"| n8
  b3["AND · 已登录且为所有者或接收者 (outside scope)"]
  b3 -.->|"Requires"| n5
```

[Open the live graph](http://127.0.0.1:8841/graph)

This is a focused view. Dashed boundaries retain original relations; open Web for the complete graph.

Still to confirm:

- 请确认这张首版业务与权限图是否符合你的意思；若需调整，指出相应节点或关系。

Confirm this understanding in the conversation, or describe a correction. Viewing the graph is not confirmation.
