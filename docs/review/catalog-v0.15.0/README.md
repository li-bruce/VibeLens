# v0.15.0 catalog and introduction update

This follow-up updates product descriptions and installation information after
the [v0.15.0 release](../../releases/v0.15.0.md). Published release archives retain
their original checksums; the README additions are a documentation follow-up.

## Content

- English and Chinese READMEs explain independent workflows and state models,
  shared source identities, and lightweight first-use setup.
- The packaged Skill README, Harness README and illustrated SkillHub overview
  carry the same feature description and current installation links.
- Harness setup now describes downloaded viewer dependencies and the separate
  observer environment, matching the shipped package.
- `skills.sh.json` supplies the Skills directory's product grouping. A real
  installation is used to check delivery and request the documented refresh.

## Channel status

| Channel | Verified state |
| --- | --- |
| GitHub Release | v0.15.0 published; all four archive checksums verified in the release record |
| Pages | v0.15.0 published |
| DeepSeek Harness | v0.15.0 plugin downloadable from GitHub; repository has the `dsh-plugin` topic |
| Skills CLI / directory | Repository introduction prepared; isolated install and directory refresh pending |
| SkillHub | v0.15.0 archive and three-image overview prepared; author submission awaits the browser connection |

The SkillHub upload must use the published archive with SHA-256
`9525ee92a6c897ddf0ded030810027e0f8f0905b1cfd603834f6389be2d7ca03`.
It contains seven catalog files and is 912,505 bytes. Existing platform-hosted
images are reused in [the prepared overview](skillhub-overview.md).

## Checks and remaining action

The documentation-link regression passed all six cases. Current document links,
the public Skills configuration schema and installation delivery are checked
separately and recorded in this directory.

The Edge browser connection could list the existing SkillHub tab, but navigation,
DOM reads and screenshots failed before page interaction. No author update was
submitted and no current login state was inferred. The owner was asked to reopen
the author dashboard and reconnect the Codex browser extension. Continue the
existing item update after reconnection; record its submitted version and review
status before calling it published.

References: [release download verification](../release-v0.15.0/published-verification.json),
[Skills directory refresh](https://skills.sh/docs/customize),
[Harness packaging](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/develop/basic/publish.md).
