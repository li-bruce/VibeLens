# v0.10.0 release review

The runtime/Skill source is frozen at `16703999a02900671b83168ed26f0d43f3414dad`.
The release delta updates the bilingual README, release notes, changelog, product
footer and archives. It does not change the validated runtime or model protocol.

| Evidence | Result and scope |
|---|---|
| [GitHub source checks](https://github.com/li-bruce/VibeLens/actions/runs/40984134971) | Passed for `1670399`: Windows/Linux source quality, Python 3.11/3.13 full verification and live database integration |
| [Engineering structure](../engineering-structure/README.md) | Scanned files/directories, source links, refresh, browser interactions and strict native examples |
| [All-layer application trial](../layer-experience/README.md) | Real file-sharing program, rename iteration, all nine layers, actual runtime values, missing-mapping failure and repair |
| [Final layer order](../layer-order/README.md) | Data structure at the bottom, migration, custom order, shared 2D/3D controls and saved views |
| [Skill ZIP manifest](manifest.json) | Complete tracked Skill, per-file hashes, archive verification and fresh installation |
| [Release preflight](preflight.json) | Package links, bilingual product copy, layer order, source formatting and ZIP consistency |

The all-layer trial's complete local gate passed with one Windows filesystem
symlink case skipped for missing host privilege. The later layer-order change ran
targeted local regressions and both native example gates. Its complete cloud
matrix subsequently passed at the exact source commit above. Earlier reports
retain their original source identities and are not relabeled as newer runs.

The ZIP excludes caches, dependency installations and local configuration. Existing
projects keep their own layout files; upgrading uses the same runtime migration
entrypoint as before. The source protocol and graph identities remain stable.

For fixed-version installation, use `vibelens-v0.10.0.zip` attached to the GitHub
release, or `skills/vibelens` at tag `v0.10.0`. Maintained documentation is English
first; conversations and the viewer support English and Chinese.

## 中文

本版包含工程结构层、布局优化、九层介绍和最终层序调整。数据结构位于底部，
自定义视图、位置、固定点与批注保留。验收材料保留真实运行、功能迭代、失败与修复。

发布包逐文件核对哈希，并进行全新安装检查。完整云端检查已在运行代码提交 `1670399`
通过。发布准备只更新文档、页脚和安装包，原始验收记录保持不变。
