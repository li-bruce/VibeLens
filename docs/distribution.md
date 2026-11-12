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
[v0.15.0 release verification](review/release-v0.15.0/README.md) records the
published archives. [Catalog updates](review/catalog-v0.15.0/README.md) distinguish
prepared material, submissions and publicly available versions.

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

The root `skills.sh.json` provides the directory's product grouping and short
description. Its [documented refresh mechanism](https://skills.sh/docs/customize)
uses a CLI installation with telemetry enabled; the directory also caches results.
Verify the visible listing after refresh before reporting it as updated.

## Release checklist

1. Update the English/Chinese README, packaged Skill README, Harness README,
   SkillHub overview and installation links together. Keep illustrations in the
   overview and link to the current release notes.
2. Publish versioned packages with their manifests and checksums. Existing release
   artifacts keep their published bytes; later description edits go to the
   repository and catalog overview.
3. Upload the released SkillHub package and updated illustrated overview through
   the author account. Record submission and public publication separately.
4. Check the Harness download and run one isolated Skills CLI installation from
   GitHub. Verify installed version and resources; leave personal/global installs
   unchanged.
5. Record channel URLs, verified versions, check results and pending platform
   actions in `docs/review/`. A prepared package or pending review is not a
   published catalog update.

## 中文

通过 GitHub、产品网站、Skills CLI 或现有 SkillHub 条目获取 VibeLens。
DeepSeek Harness 使用独立插件包，安装说明列出了已测试版本。
SkillHub 包在首次使用时校验并解包 Skill 源码，再下载查看器依赖；离线包已包含这些依赖。
各渠道的发布状态记录在本轮验收材料中。
