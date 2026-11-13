# Installation entry points

The product homepage now offers Skills CLI, GitHub release downloads, SkillHub
and the DeepSeek Harness plugin guide. A separate Codex prompt shows how to begin
after installation. All explanatory copy follows the page's English/Chinese
language selection.

## Verified destinations

- GitHub's latest-release API returned `v0.15.0`, including the Skill ZIP and
  `dsh-vibelens-0.15.0.tgz` plugin.
- [SkillHub](https://skillhub.cn/skills/indiv-skii/vibelens) publicly displayed
  v0.15.0, its installation prompt and ZIP download on 2026-11-13. The old
  `/skills/user_fbf26156/vibelens` entry returned **Skill Not Found**. Current
  README and distribution links now use the working address.
- The Skills CLI command matches the previously verified repository install.
  This change does not claim a verified Skills.sh directory listing.
- Harness links to the maintained plugin installation guide rather than a
  separate marketplace listing.

## Checks

- `node tools/test_product_demo.mjs`: passed, including bilingual product copy.
- `python tests/test_document_links.py`: six tests passed.
- Prettier, ESLint for changed JavaScript, and `git diff --check`: passed.
- Browser: English/Chinese labels and prompts, localized usage links, command
  and prompt copy feedback, and the four installation options were inspected.
  No console errors were reported. The browser host did not expose the webpage's
  clipboard value to its clipboard reader; the copy feedback check is recorded
  separately from a byte-for-byte clipboard assertion.

This update changes the homepage and maintained documentation. Published release
archives retain their existing bytes and version.
