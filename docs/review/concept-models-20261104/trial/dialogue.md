# Independent Skill trial — synthetic conversation

The developer is an independent AI agent. User replies are AI-simulated for this
acceptance and do not represent a human accepting these application rules.

## 1. Request and clarification

**User:** $vibelens 我要做一个同事之间共享文件的小应用。我上传文件后能共享给指定同事，也能撤销共享；同事可以查看别人共享给自己的文件并下载。先做本地简洁网页。

**Developer:** 可以。先确认三件影响实现的事：
1. 要让程序按状态声明运行，还是保留普通代码、用图观察？两种方式都有图和运行记录。
2. 本地文件配 SQLite 足够这个小应用。人员先用固定测试账号切换，可以吗？
3. 第一版一个文件可以同时共享给多人吗？撤回后，已经拿到下载链接的人还能再次下载吗？

**User (simulated):** 保留我自己的代码组织，只用图观察。文件就放本地，信息用SQLite吧。先固定Alice、Bob、Carol三个测试用户，用下拉框切换。第一版一个文件给一个人，换人共享就替换原来的。只有上传者能共享和撤回，撤回后旧链接的下一次下载必须拒绝。

**Developer:** 第一版按“上传—指定接收者—看到文件—下载”组织。上传者可以撤回或替换接收者；每次下载读取当前授权。文件存储和运行记录放在 var/，不作为源码扫描；app.py、service.py、bo_integration.py、bo_stategraph/ 中的声明属于项目源码。

The next entries include the three actual generated previews, followed by the
simulated confirmation, before application implementation.


## business preview

# Business network draft

```mermaid
flowchart LR
  n0["File sharing"]
  n1["See received files"]
  n2["actor"]
  n3["grant"]
  n4["Read shared file"]
  n5["Revoke access"]
  n6["Share file"]
  n7["Upload file"]
  n0 -->|"contains"| n1
  n0 -->|"contains"| n4
  n0 -->|"contains"| n5
  n0 -->|"contains"| n6
  n0 -->|"contains"| n7
  n1 -->|"Download file"| n4
  n6 -->|"Recipient sees file"| n1
  n6 -->|"Owner withdraws access"| n5
  n7 -->|"Choose recipient"| n6
  b0["active-grant (outside scope)"]
  n3 -.->|"describes_fact"| b0
  b1["actor-id (outside scope)"]
  n2 -.->|"describes_fact"| b1
  b2["owner-id (outside scope)"]
  n3 -.->|"describes_fact"| b2
  b3["recipient-id (outside scope)"]
  n3 -.->|"describes_fact"| b3
  b4["policy-operation:read (outside scope)"]
  n1 -.->|"requires_decision"| b4
  b5["policy-operation:read (outside scope)"]
  n4 -.->|"requires_decision"| b5
  b6["policy-operation:manage (outside scope)"]
  n5 -.->|"requires_decision"| b6
  b7["policy-operation:manage (outside scope)"]
  n6 -.->|"requires_decision"| b7
  b8["Recipient grant (outside scope)"]
  n1 -.->|"reads_state"| b8
  b9["Recipient grant (outside scope)"]
  n4 -.->|"reads_state"| b9
  b10["Recipient grant (outside scope)"]
  n5 -.->|"changes_state"| b10
  b11["Recipient grant (outside scope)"]
  n6 -.->|"changes_state"| b11
  b12["revoke (outside scope)"]
  n5 -.->|"action_requests_event"| b12
  b13["share (outside scope)"]
  n6 -.->|"action_requests_event"| b13
  b14["Recipient grant (outside scope)"]
  b14 -.->|"state_subject"| n3
```

[Open the live graph](http://127.0.0.1:8916/graph)

This is a focused view. Dashed boundaries retain original relations; open Web for the complete graph.

Confirm this understanding in the conversation, or describe a correction. Viewing the graph is not confirmation.


## state preview

# State model draft

```mermaid
flowchart LR
  n0["revoke"]
  n1["share"]
  n2["may_manage"]
  n3["Recipient grant"]
  n4["active"]
  n5["inactive"]
  n6["grant-replace"]
  n7["grant-revoke"]
  n8["grant-share"]
  n1 -->|"requests_transition"| n6
  n0 -->|"requests_transition"| n7
  n1 -->|"requests_transition"| n8
  n3 -->|"contains"| n4
  n3 -->|"contains"| n5
  n3 -->|"declares_event"| n0
  n3 -->|"declares_event"| n1
  n3 -->|"declares_guard"| n2
  n4 -->|"share"| n4
  n4 -->|"revoke"| n5
  n5 -->|"share"| n4
  n6 -->|"guarded_by"| n2
  n7 -->|"guarded_by"| n2
  n8 -->|"guarded_by"| n2
  n6 -->|"declares_target"| n4
  n7 -->|"declares_target"| n5
  n8 -->|"declares_target"| n4
  b0["policy-operation:manage (outside scope)"]
  n2 -.->|"guard_resolves_decision"| b0
  b1["See received files (outside scope)"]
  b1 -.->|"reads_state"| n3
  b2["Read shared file (outside scope)"]
  b2 -.->|"reads_state"| n3
  b3["Revoke access (outside scope)"]
  b3 -.->|"changes_state"| n3
  b4["Share file (outside scope)"]
  b4 -.->|"changes_state"| n3
  b5["policy-operation:manage (outside scope)"]
  n6 -.->|"transition_guarded_by"| b5
  b6["policy-operation:manage (outside scope)"]
  n7 -.->|"transition_guarded_by"| b6
  b7["Revoke access (outside scope)"]
  b7 -.->|"action_requests_event"| n0
  b8["policy-operation:manage (outside scope)"]
  n8 -.->|"transition_guarded_by"| b8
  b9["Share file (outside scope)"]
  b9 -.->|"action_requests_event"| n1
  b10["grant (outside scope)"]
  n3 -.->|"state_subject"| b10
```

[Open the live graph](http://127.0.0.1:8916/graph)

This is a focused view. Dashed boundaries retain original relations; open Web for the complete graph.

Confirm this understanding in the conversation, or describe a correction. Viewing the graph is not confirmation.


## rules preview

# Rule network draft

```mermaid
flowchart LR
  n0["active-grant"]
  n1["actor-id"]
  n2["owner-id"]
  n3["recipient-id"]
  n4["policy-predicate:same_identity"]
  n5["active"]
  n6["actor"]
  n7["is_owner"]
  n8["is_recipient"]
  n9["may_read"]
  n10["owner"]
  n11["recipient"]
  n4 -->|"data"| n7
  n6 -->|"data"| n7
  n10 -->|"data"| n7
  n4 -->|"data"| n8
  n6 -->|"data"| n8
  n11 -->|"data"| n8
  n8 -->|"guard"| n9
  n5 -->|"guard"| n9
  n5 -->|"decision_reads_fact"| n0
  n6 -->|"decision_reads_fact"| n1
  n10 -->|"decision_reads_fact"| n2
  n11 -->|"decision_reads_fact"| n3
  b0["grant (outside scope)"]
  b0 -.->|"describes_fact"| n0
  b1["actor (outside scope)"]
  b1 -.->|"describes_fact"| n1
  b2["grant (outside scope)"]
  b2 -.->|"describes_fact"| n2
  b3["grant (outside scope)"]
  b3 -.->|"describes_fact"| n3
  b4["policy-operation:manage (outside scope)"]
  n7 -.->|"decision_result"| b4
  b5["policy-operation:read (outside scope)"]
  n9 -.->|"decision_result"| b5
```

[Open the live graph](http://127.0.0.1:8916/graph)

This is a focused view. Dashed boundaries retain original relations; open Web for the complete graph.

Confirm this understanding in the conversation, or describe a correction. Viewing the graph is not confirmation.


**Developer:** 业务流程、授权的两个状态，以及共享和下载各自的判断已经画出来了。下载只读授权状态；共享和撤回会改变它。可以在 http://127.0.0.1:8916/graph 查看。这样与你想做的一致吗？

**User (simulated):** 对，就是这样。先按这个做。


## Iteration 2 — synthetic conversation

**User U4:** 共享给多个人后，我只想撤回其中一个人的权限，其他人的继续有效。

**Developer:** 我理解为：Alice 同时共享给 Bob 和 Carol；撤回 Bob 后，Bob 的旧下载地址失效，Carol 仍能下载。每一份“文件与接收者”的授权各自有启用、撤回状态。是这样吗？

**Synthetic user:** 对，只撤回我选中的那个人，其他人的别动。

**Developer:** 业务步骤保持上传、共享、查看、下载和撤回；这轮改变共享与撤回的对象范围。下面是本轮确认图，状态以“文件 + 接收者”区分，所有者规则仍然共用。


# Business network draft

```mermaid
flowchart LR
  n0["File sharing"]
  n1["See received files"]
  n2["actor"]
  n3["grant"]
  n4["Read shared file"]
  n5["Revoke access"]
  n6["Share file"]
  n7["Upload file"]
  n0 -->|"Contains"| n1
  n0 -->|"Contains"| n4
  n0 -->|"Contains"| n5
  n0 -->|"Contains"| n6
  n0 -->|"Contains"| n7
  n1 -->|"Download file"| n4
  n6 -->|"Recipient sees file"| n1
  n6 -->|"Owner withdraws access"| n5
  n7 -->|"Choose recipient"| n6
  b0["active-grant (outside scope)"]
  n3 -.->|"Describes"| b0
  b1["actor-id (outside scope)"]
  n2 -.->|"Describes"| b1
  b2["owner-id (outside scope)"]
  n3 -.->|"Describes"| b2
  b3["recipient-id (outside scope)"]
  n3 -.->|"Describes"| b3
  b4["policy-operation:read (outside scope)"]
  n1 -.->|"Requires"| b4
  b5["policy-operation:read (outside scope)"]
  n4 -.->|"Requires"| b5
  b6["policy-operation:manage (outside scope)"]
  n5 -.->|"Requires"| b6
  b7["policy-operation:manage (outside scope)"]
  n6 -.->|"Requires"| b7
  b8["Recipient grant (outside scope)"]
  n1 -.->|"Reads state"| b8
  b9["Recipient grant (outside scope)"]
  n4 -.->|"Reads state"| b9
  b10["Recipient grant (outside scope)"]
  n5 -.->|"Changes state"| b10
  b11["Recipient grant (outside scope)"]
  n6 -.->|"Changes state"| b11
  b12["revoke (outside scope)"]
  n5 -.->|"Triggers"| b12
  b13["share (outside scope)"]
  n6 -.->|"Triggers"| b13
  b14["Recipient grant (outside scope)"]
  b14 -.->|"State of"| n3
```

[Open the live graph](http://127.0.0.1:8916/graph)

This is a focused view. Dashed boundaries retain original relations; open Web for the complete graph.

Confirm this understanding in the conversation, or describe a correction. Viewing the graph is not confirmation.


# State model draft

```mermaid
flowchart LR
  n0["revoke"]
  n1["share"]
  n2["may_manage"]
  n3["Recipient grant"]
  n4["active"]
  n5["inactive"]
  n6["grant-replace"]
  n7["grant-revoke"]
  n8["grant-share"]
  n1 -->|"Triggers"| n6
  n0 -->|"Triggers"| n7
  n1 -->|"Triggers"| n8
  n3 -->|"Contains"| n4
  n3 -->|"Contains"| n5
  n3 -->|"Event"| n0
  n3 -->|"Event"| n1
  n3 -->|"Condition"| n2
  n4 -->|"share"| n4
  n4 -->|"revoke"| n5
  n5 -->|"share"| n4
  n6 -->|"Requires"| n2
  n7 -->|"Requires"| n2
  n8 -->|"Requires"| n2
  n6 -->|"Enters"| n4
  n7 -->|"Enters"| n5
  n8 -->|"Enters"| n4
  b0["policy-operation:manage (outside scope)"]
  n2 -.->|"Evaluates"| b0
  b1["See received files (outside scope)"]
  b1 -.->|"Reads state"| n3
  b2["Read shared file (outside scope)"]
  b2 -.->|"Reads state"| n3
  b3["Revoke access (outside scope)"]
  b3 -.->|"Changes state"| n3
  b4["Share file (outside scope)"]
  b4 -.->|"Changes state"| n3
  b5["policy-operation:manage (outside scope)"]
  n6 -.->|"Requires"| b5
  b6["policy-operation:manage (outside scope)"]
  n7 -.->|"Requires"| b6
  b7["Revoke access (outside scope)"]
  b7 -.->|"Triggers"| n0
  b8["policy-operation:manage (outside scope)"]
  n8 -.->|"Requires"| b8
  b9["Share file (outside scope)"]
  b9 -.->|"Triggers"| n1
  b10["grant (outside scope)"]
  n3 -.->|"State of"| b10
```

[Open the live graph](http://127.0.0.1:8916/graph)

This is a focused view. Dashed boundaries retain original relations; open Web for the complete graph.

Confirm this understanding in the conversation, or describe a correction. Viewing the graph is not confirmation.


**Synthetic user U5:** 图里的步骤没变，每个人的授权单独算，这样对。开始改吧。

Implementation follows this confirmation. C1 remains unchanged; C2 records the new identity and selected-recipient meaning.

## Execution notes after the confirmed iteration

These are the testing agent's observations, not additional user answers.

- The actual v2 application shared one file with Bob and Carol. Revoking Bob
  returned 200; Bob's old download URL returned 403, while Carol still received
  the original bytes. The complete on/off/fault gate passed.
- Browser recording exposed a shared probe defect: a filtered read still
  submitted a snapshot with no evidence ID. The adapters were repaired first;
  a real repeat recorded nine events with zero producer errors.
- A second test hid a new grant's events and then restored full capture. The
  local adapter had marked its initial state as already captured. A separately
  begun maintenance change now marks initialization only after queuing actual
  evidence. The same native grant's active state and revision were then observed;
  no business rule or synthetic confirmation changed.
- Failed receipts, each strict acceptance round and the final portable sources
  are linked from the trial README. The final viewer and browser evidence use
  the repaired application; historical receipts remain unchanged in the archive.
