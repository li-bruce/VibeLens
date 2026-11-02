# Business network draft

```mermaid
flowchart LR
  n0["指定同事权限已生效"]
  n1["后台投递撤销通知"]
  n2["下载文件"]
  n3["各自的消息列表"]
  n4["上传者撤销指定共享"]
  n5["共享已撤销"]
  n6["共享通知待投递"]
  n7["查看文件"]
  n0 -->|"指定同事"| n2
  n0 -->|"指定同事"| n7
  n1 -->|"写入原接收同事的消息列表"| n3
  n0 -->|"已生效也可撤销"| n4
  n6 -->|"等待中也可撤销"| n4
  n4 -->|"提交撤销立即收回共享权限"| n5
  n4 -->|"通知异步投递，不阻塞撤销"| n1
  b0["AND · 允许查看与下载 (outside scope)"]
  b0 -.->|"Requires"| n2
  b1["AND · 允许上传者撤销共享 (outside scope)"]
  b1 -.->|"Requires"| n4
  b2["AND · 允许查看与下载 (outside scope)"]
  b2 -.->|"Requires"| n7
  b3["后台投递审核通知 (outside scope)"]
  b3 -.->|"写入上传者的消息列表"| n3
  b4["后台投递共享通知 (outside scope)"]
  b4 -.->|"投递成功后权限生效"| n0
  b5["后台投递共享通知 (outside scope)"]
  n6 -.->|"后台稍后执行"| b5
  b6["后台投递共享通知 (outside scope)"]
  b6 -.->|"写入接收同事的消息列表"| n3
  b7["上传者指定同事共享 (outside scope)"]
  b7 -.->|"创建共享任务"| n6
```

[Open the live graph](http://127.0.0.1:50950/graph)

This is a focused view. Dashed boundaries retain original relations; open Web for the complete graph.

Confirm this understanding in the conversation, or describe a correction. Viewing the graph is not confirmation.
