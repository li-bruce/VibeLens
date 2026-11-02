# Share revocation request

再加一个撤销共享的功能。上传者可以撤销给某位同事的共享，对方要立即不能再下载。还在等待通知的共享也能撤销，旧通知后来送达也不能恢复权限。撤销通知仍然发给这位同事。

## Authority clarification

原有规则允许管理员始终查看、下载文件。如果被撤销共享的同事也是管理员，撤销后是否仍保留其管理员权限？这决定撤销规则与既有管理员权限如何衔接。

Status: pending answer; no administrator policy override is assumed.

## Explicit answer

保留管理员原有权限，撤销只移除共享授权

Resolved: revoke only removes the designated share basis.

## Explicit graph confirmation

这张流程图符合我的意思，就按这个做。
Source: delegated user message in this continuation, 2026-11-01.
