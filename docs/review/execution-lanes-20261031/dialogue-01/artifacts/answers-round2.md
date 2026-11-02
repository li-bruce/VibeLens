# Actual answers and follow-up

## U_DETAIL: Detailed business answer

Forwarded in the current chat from source chat `01a1439a-dceb-7ba2-bada-546619caf220`:

> 就按状态图来驱动吧。上传时由上传者从已有用户里选审核人，不能自己审核自己上传的文件。审核通过后，还是由上传者选一个接收人并发起分享。
>
> 访问先做文件信息和下载，暂时不用网页预览。上传者和指定审核人在审核前可以下载，其他人不可以；接收人要等审核通过、并且确实分享给他以后才能下载。
>
> 先把按这些规则更新后的流程图给我看一下。

## U_PANEL: Actual clarification-panel reply

- Mode: `drive：由状态声明驱动业务执行`
- Authority: `上传者决定，管理员，上传者`
- Access: `最简单的查看和下载就行`

## A_ADMIN: Actual follow-up question

你在第二项回答中的“管理员”具体指什么？它是否修改了你前面“从已有用户中选审核人，不能审核自己上传的文件”的规则？

At this round no answer to A_ADMIN had been recorded. The short word `管理员` did not establish a self-review exception or a restriction to administrator reviewers. The later forwarded message and latest direct correction are preserved in `answers-round3.md`; consult `current-status.md` for the current interpretation.

## Environment-only follow-up

> 补充一个运行环境的检查结果：我从宿主机访问 http://127.0.0.1:62428/api/design 返回了 200，实际进程也是刚才启动的 89976。你那边的超时应先按执行环境的本地网络隔离排查，别把它当作业务规则或框架缺陷。这条只是环境信息，前面回答的业务规则没有变化。

This is environment evidence, not a new business rule. Independent host HTTP checks and an actual in-app-browser inspection also succeeded after the isolated sandbox process was stopped.
