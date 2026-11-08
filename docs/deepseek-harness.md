# VibeLens for DeepSeek Harness

Use the same connected models, observer and viewer from a Harness conversation.

## Install

This release targets **DeepSeek Harness 0.2.2-rc.1** and **Node.js 24.9+**.
Install that Harness version first, then add the prebuilt plugin to your profile:

```sh
npm install -g @deepseek-ai/dsh@0.2.2-rc.1
dsh plugin --profile web add https://github.com/li-bruce/VibeLens/releases/download/v0.14.0/dsh-vibelens-0.14.0.tgz
dsh web
```

For an existing desktop installation of the supported Harness version, use
`--profile desktop` instead. The tarball contains the full Skill, Python scripts,
native adapters and Web assets. Python 3.11+ runs the observer; install its pinned
`skill/requirements.txt` dependencies in the project environment when adopting it.

Start a project conversation:

```text
/vibelens I want a file-sharing application. Owners can share with named
recipients and revoke their access. Show the business, state and rule graphs
before implementation, and ask about unclear details.
```

Continue development in ordinary language. To change a view:

```text
/vibelens Focus on revoking access and the next download. Show decisions and parameters.
```

## Host integration

The bundle adds one provider to Harness's native skill registry. Its invocation
policy is `modelInvocable: false, userInvocable: true`. Harness loads the body only
for explicit user invocation. A small hook adds the actual session ID and working
directory to that invocation, enabling conversation-scoped view controls.

The Python control CLI uses `--host deepseek-harness --conversation SESSION_ID`.
It preserves the original user message, separates host namespaces, and checks the
project's actual observer identity. Other conversations receive no VibeLens body.

The package does not replace Harness's agent, tool registry, working-directory
service or other skills. Business execution remains in the project; the external
observer keeps its existing JSON protocols. Remove the plugin with:

```sh
dsh plugin --profile web remove dsh-vibelens
```

## Reproduce the checks

```sh
python tools/build_distribution.py
mkdir -p .validation/harness-package
tar -xzf .validation/distribution/dsh-vibelens-0.14.0.tgz -C .validation/harness-package
npm ci --prefix tools/harness-tests
node tools/harness-tests/test.mjs
```

[Release evidence](review/harness-distribution-20261105/README.md) records the exact
host, install, invocation and resource-loading results. Compatibility is pinned
because Harness's developer-preview APIs can change between releases.

The official project documents both npm and tarball installation and recommends
the GitHub `dsh-plugin` topic for discovery:
[packaging](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/develop/basic/publish.md),
[discovery](https://github.com/deepseek-ai/deepseek-harness#community-and-support).
