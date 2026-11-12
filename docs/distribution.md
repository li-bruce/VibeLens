# Find and install VibeLens

| Channel | Entry |
|---|---|
| GitHub | [Source](https://github.com/li-bruce/VibeLens), [versioned downloads](https://github.com/li-bruce/VibeLens/releases/latest) |
| Product website | [Features](https://liblog.vip/VibeLens/), [interactive walkthrough](https://liblog.vip/VibeLens/demo.html) |
| Skills CLI | `npx skills add li-bruce/VibeLens --skill vibelens` |
| SkillHub | [VibeLens by user_fbf26156](https://skillhub.cn/skills/user_fbf26156/vibelens) |
| DeepSeek Harness | [Plugin installation and compatibility](deepseek-harness.md) |

## Release packages

Each release builds these artifacts from the same canonical Skill:

- `vibelens-vVERSION.zip`: owned code, instructions, notices and dependency lock.
- `dsh-vibelens-VERSION.tgz`: a prebuilt Harness plugin with that same Skill.
- `vibelens-skillhub-vVERSION.zip`: a compact catalog package. SkillHub limits
  uploads to 200 files, so this package contains the complete resource archive
  and a local Python bootstrap. It verifies every file and extracts the Skill on
  first explicit use. Viewer resources use the same dependency setup as direct installation.
- `vibelens-offline-vVERSION.zip`: an optional complete Skill with verified
  viewer dependencies and the libavoid corresponding-source archive.

The normal packages download exact-version assets from a CDN on first use,
then fall back to a pinned GitHub commit. Every file is checked by size and
SHA-256. Installed files and a shared cache support subsequent offline use.
Source installation also supports `tools/install_skill.py --defer-dependencies`
and `--offline`. See [setup and recovery](../skills/vibelens/references/dependency-distribution.md).

`SHA256SUMS` identifies the archives. `manifest.json` records their source files.
[Build and verification records](review/harness-distribution-20261105/README.md)
separate published versions from submissions waiting for catalog review.

## Maintaining the descriptions

The English [README](../README.md), [Chinese README](../README.zh-CN.md), packaged
[Skill README](../skills/vibelens/README.md), and
[SkillHub overview](distribution/skillhub.zh-CN.md) share the same product story.
Repository copies use absolute image and documentation links. SkillHub requires
images uploaded through its overview editor; replace the three image URLs with
the returned hosted URLs before submission, keeping their original positions. Product descriptions
cover the model, connected graph, focused views and runtime inspection; application
stories belong in the interactive demo.

Harness's official project supports tarball installation and recommends the
`dsh-plugin` GitHub topic for discovery. This release does not claim a separate
marketplace listing. Skills.sh discovery is based on CLI usage; repository
publication does not guarantee a ranking.

## 中文

通过 GitHub、产品网站、Skills CLI 或现有 SkillHub 条目获取 VibeLens。
DeepSeek Harness 使用独立插件包，安装说明列出了已测试版本。
SkillHub 包在首次使用时校验并解包完整资源；GitHub 完整包可直接安装。
各渠道的发布状态记录在本轮验收材料中。
