# A revocation that leaves access open

The developer is building a small file-sharing application. An owner uploads a file, shares it with a colleague and can revoke that person's access. A recipient may view or download, but cannot share it onward. The owner's own access remains available.

| Stage | Person's action | Visible evidence | What VibeLens contributes |
| --- | --- | --- | --- |
| Confirm | Discuss the application with Codex; clarify who controls sharing and when revocation takes effect | A compact business overview, the file-state transitions, and shared permission conditions | Confirm the intended model before implementation |
| Record | Use VibeLens to follow a recorded share, download, revoke and second download; operate the miniature application controls | The recipient can still download after revocation | See actual execution and return values, then revisit the relevant event |
| Inspect | Keep the revocation action, its input identities and the deletion result; open the mapped source | `rows = 0`, `removed = false`, state still `shared`; the predicate compares `recipient_id` with the owner's `actor` | Narrow the graph and connect runtime evidence to the exact code |
| Refine | Tell Codex the finding: revocation used the owner's ID instead of the selected recipient's ID | AI changes the predicate to `recipient_id`; the same saved view remains available | Carry a precise finding back into the coding dialogue |
| Verify | Repeat the same operation on the repaired build | One row removed, remaining grant count zero, state `private`, recipient download denied; owner access retained | Compare the updated source, graph and actual result |

The five stages combine repeated exploration. Codex dialogue is shown for agreement and implementation changes. Recording, filtering, source reading and playback are actions in VibeLens. Application controls select the corresponding real recorded operations on the static demo; they do not run a second implementation of permission logic.

The public page uses short story copy. The original recording, source, mutation checks and teaching-defect provenance remain available through the example and review links. This case is not evidence that the separate v0.12.1 independent chat passed acceptance.

## 中文梗概

我要做一个文件共享应用：我上传文件后，可以共享给同事，也可以取消共享。同事能查看和下载，不能转给别人。

先在 Codex 中确认业务、状态和权限。程序运行后，我在 VibeLens 中查看一次“共享—下载—取消共享—再次下载”的记录，发现取消后同事仍能下载。沿撤销链路下钻，看到删除了 0 行，再打开源码：删除条件用了所有者的 ID。把这个发现告诉 Codex，AI 修改为选中的接收者 ID。保留同一观察视图再次运行，确认删除 1 行，接收者被拒绝，所有者仍可访问。
