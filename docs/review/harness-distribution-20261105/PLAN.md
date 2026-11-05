# Distribution and DeepSeek Harness release

## Scope

Refresh the visual product README and existing catalog entries, package VibeLens
for DeepSeek Harness, test the installed artifact, and publish a versioned release.
Keep the native state engine, observation protocol and per-conversation activation.

## Work list

- [x] Inspect the maintained repository and official Harness plugin/skill contracts.
- [x] Rewrite English and Chinese product READMEs with current, traceable visuals.
- [x] Add an explicit-invocation Harness skill provider and reproducible package.
- [x] Test real Harness registration, resource loading, isolation and installation.
- [x] Run source, package, documentation and relevant product regressions.
- [x] Publish the release and Pages, submit the SkillHub update, and verify each public status.
- External status: SkillHub 0.13.0 is awaiting its security review; the public entry remains on 0.7.1.

## Distribution inventory

GitHub, Pages and the existing SkillHub entry are the authorized channels.
The owner supplied https://skillhub.cn/skills/user_fbf26156/vibelens and completed
login. The previous public version was 0.7.1. The 0.13.0 submission is under security review and contains the
complete seven-file transport, a branded icon and a three-image product overview.
The full archive remains directly installable from GitHub; Harness uses its
supported tarball plugin path. Skills CLI continues to read the public repository.

User refinements included: desktop-focused tool development, directional transfer
arrows, matching 2D/3D type vocabulary, and product-only homepage copy.

## Primary sources

- [Harness packaging](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/develop/basic/publish.md)
- [Harness skill registry](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/skill/skill/README.md)
- [Harness local skill policy](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/skill/skill-filesystem/README.md)

Harness supports packaged skill providers with separate model/user invocation
policies. Use its human-invocation path, ship complete resources, and verify the
actual released API rather than assuming the moving master branch matches npm.
