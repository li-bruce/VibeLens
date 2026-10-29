# Business network draft

```mermaid
flowchart LR
  n0["该文件不可见，下载被拒绝"]
  n1["每次请求读取并判断当前权限"]
  n2["接收者下载文件"]
  n3["AND · 已登录、是所有者且接收者存在 · all"]
  n4["当前文件与指定接收者的共享关系"]
  n5["其他接收者与所有者继续访问"]
  n6["所有者取消指定接收者的共享"]
  n7["共享文件（仅所有者可操作）"]
  n1 -->|"所有者或当前接收者才允许"| n2
  n1 -->|"取消后下一次请求被拒绝"| n0
  n4 -->|"请求时读取当前关系"| n1
  n3 -->|"Requires"| n6
  n3 -->|"Requires"| n7
  n6 -->|"只移除所选文件与接收者的关系"| n4
  n6 -->|"保留其他关系与所有权"| n5
  n7 -->|"建立或重新建立指定关系"| n4
  n6 -->|"以后可以再次共享"| n7
  b0["接收者查看文件名、大小、共享人 (outside scope)"]
  b0 -.->|"点击下载"| n2
  b1["Rules (outside scope)"]
  b1 -.->|"Rule expression"| n3
  b2["已登录 (outside scope)"]
  b2 -.->|"all"| n3
  b3["当前用户是所有者 (outside scope)"]
  b3 -.->|"all"| n3
  b4["接收者是已有用户 (outside scope)"]
  b4 -.->|"all"| n3
  b5["AND · 已登录且为所有者或接收者 (outside scope)"]
  b5 -.->|"Requires"| n2
  b6["所有者选择已有用户（示例：许宁） (outside scope)"]
  b6 -.->|"一次选择一个已有用户"| n7
  b7["接收者查看文件名、大小、共享人 (outside scope)"]
  n7 -.->|"建立所有者与接收者关系"| b7
  b8["周岚：未收到该文件的共享 (outside scope)"]
  b8 -.->|"无该文件共享权限"| n0
```

[Open the live graph](http://127.0.0.1:8843/graph)

This is a focused view. Dashed boundaries retain original relations; open Web for the complete graph.

Confirm this understanding in the conversation, or describe a correction. Viewing the graph is not confirmation.
