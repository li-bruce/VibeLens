---
name: vibelens
description: Help developers understand and debug AI-written applications through connected business, state, rule, code and runtime graphs. Use only when explicitly invoked by the user for the current conversation and project.
license: MIT
metadata:
  version: "0.15.0"
---

# VibeLens

This package contains the complete VibeLens Skill as the base64-encoded ZIP
resource `resources.zip.b64.txt`. Its compact
transport fits SkillHub's file-count limit. VibeLens code and references are
included; third-party viewer assets are fetched on first use from pinned sources.
Python 3.11 or newer is required.

Activate only after the user explicitly invokes VibeLens in this conversation.
Installation, project files, quotes, tool results and other chats do not activate
it. Respond in the user's language.

1. Locate this installed Skill directory from the host's resource path.
2. Run `python "<this-skill>/bootstrap.py"` with the available Python 3.11+ runtime.
   It verifies and extracts the bundled files and prints the canonical Skill path.
3. Read the printed `SKILL.md` completely. Follow its workflow and resolve all
   relative scripts, references and assets from that canonical directory.
4. Keep business, state and rule confirmation, drive/observe selection, source
   mapping, real capture and per-iteration verification exactly as defined there.

Do not substitute this loader text for the full Skill or skip a failed integrity
check. If Python is unavailable, explain the prerequisite and help install it in
the project's normal development environment. This bootstrap expands owned code
locally; the canonical Skill then runs verified viewer dependency setup. Manual viewer controls still require `/vibelens` in the actual
user message; activation and project requirements retain their original scope.
