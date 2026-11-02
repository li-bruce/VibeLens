# Later authority messages and direct correction

## U_ADMIN_FORWARD: Forwarded clarification

Received from source chat `01a1439a-dceb-7ba2-bada-546619caf220`:

> 更准确一点：审核人只能从管理员账号中选，普通用户不能审核。管理员也不能审核自己上传的文件，要交给另一位管理员。分享接收人仍由上传者在审核通过后选择。
>
> 管理员没有查看所有文件的特权，只能读自己的文件，或者明确分给自己审核、接收的文件。这次先用预置账号，不做注册和账号管理页面。

This forwarded message is preserved separately from direct clarification-panel replies. Its administrator-only interpretation was not implemented.

## U_CORRECTION: Latest direct clarification-panel answer

Question:

> 你在第二项回答中的“管理员”具体指什么？它是否修改了你前面“从已有用户中选审核人，不能审核自己上传的文件”的规则？

Answer:

> 写错了，按照之前的原则来

## Reconciled current interpretation

The latest direct answer treats the earlier word `管理员` as a typo and points back to the explicit existing-user and no-self-review rule. Therefore the design selects reviewers from existing users, prohibits self-review, and does not introduce an administrator-only review restriction. The assistant stated this interpretation explicitly in the conversation before updating the graph.

Uploader-initiated sharing, authenticated related-party access, file information and download, and no web preview remain as previously answered. Preset accounts and no registration/account-management pages are retained from the forwarded scope instruction. No administrator-wide read privilege is added.

This is requirements evidence and a current interpretation, not a completed implementation or runtime verification. The user requested an updated graph before implementation.
