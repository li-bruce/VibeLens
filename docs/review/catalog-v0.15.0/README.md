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
| Skills CLI | GitHub installation passed; all 387 installed files match the maintained Skill |
| Skills directory | Grouping configuration published; the public listing is not yet verified |
| SkillHub | v0.15.0 archive and three-image overview prepared; submission remains blocked by browser control |

The SkillHub upload must use the published archive with SHA-256
`9525ee92a6c897ddf0ded030810027e0f8f0905b1cfd603834f6389be2d7ca03`.
It contains seven catalog files and is 912,505 bytes. Existing platform-hosted
images are reused in [the prepared overview](skillhub-overview.md).

## Checks and remaining action

The documentation-link regression passed all six cases. Current document links,
the public Skills configuration schema and installation delivery are checked
separately and recorded in this directory.

The [isolated Skills CLI installation](skills-install.json) completed after a
sandbox authentication failure and an approved retry. The installed version is
0.15.0. All 387 tracked files match commit `35985d2a`; explicit invocation and the
dependency lock are preserved. Personal and global Skill installations were not
changed. The [directory check](skills-directory.json) did not verify a public
listing, so delivery and directory visibility are reported separately.

The [release CI check](release-ci.json) confirms all nine jobs passed, including
the browser/Timeline, live database, Harness, source-quality and Python matrix jobs.

The Edge browser connection can list the SkillHub author dashboard, but DOM
reads and screenshots fail before page interaction. The owner reconnected the
extension; the same problem persisted after rebuilding the browser session.
No author update was submitted and no current login state was inferred. Codex
restart was requested. Continue the existing item update when browser control
is restored; record its submitted version and review status before calling it
published. The prepared archive and overview are unchanged.

References: [release download verification](../release-v0.15.0/published-verification.json),
[Skills directory refresh](https://skills.sh/docs/customize),
[Harness packaging](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/develop/basic/publish.md).
