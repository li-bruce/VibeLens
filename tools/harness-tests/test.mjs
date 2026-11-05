/** Exercise the shipped provider against the real pinned Harness skill runtime.
 * The host registry, invocation parser, policy checks and body renderer are real.
 * Session history and the agent loop are minimal fixtures; no LLM answer is mocked
 * into application-acceptance evidence.
 */
import assert from "node:assert/strict";
import { readFile, mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";

const root = fileURLToPath(new URL("../../", import.meta.url));
const require = createRequire(
  process.env.HARNESS_PACKAGES
    ? path.join(process.env.HARNESS_PACKAGES, "../package.json")
    : import.meta.url,
);
const load = (name) => import(pathToFileURL(require.resolve(name)).href);
const { Context } = await load("@deepseek-ai/cordis");
const { SkillRegistry, isModelInvocable, isUserInvocable } = await load("@deepseek-ai/dsh-skill");
const nativeConsumer = await load("@deepseek-ai/dsh-tool-skill");
const pluginRoot =
  process.env.VIBELENS_PLUGIN || path.join(root, ".validation/harness-package/package");
const plugin = await import(pathToFileURL(path.join(pluginRoot, "index.mjs")).href);
const ctx = new Context();
const registryFiber = ctx.plugin(SkillRegistry);
await registryFiber.await();
const toolMap = new Map(),
  checks = [];
const workingDirectory = { ensure: async (agent) => agent.cwd };
// Use the native consumer's handlers and execute callback with controlled inputs.
const host = {
  skills: ctx.skills,
  workingDirectory,
  tools: { register: (tool) => toolMap.set(tool.name, tool), get: (name) => toolMap.get(name) },
  on: (event, handler, options) => {
    assert.equal(event, "agent/pre-step");
    return ctx.on(event, handler, options);
  },
};
nativeConsumer.apply(host);
plugin.apply(host);
const check = (name, callback) =>
  Promise.resolve()
    .then(callback)
    .then(() => checks.push(name));
const agent = (id, cwd) => ({ id, cwd, session: { seq: 0, surface: { nodes: [] } } });
const first = agent("harness-chat-a", "/project-a"),
  second = agent("harness-chat-b", "/project-b");
const user = (text, kind = "user") => ({
  id: "input",
  source: { kind },
  content: [{ type: "text", text }],
});
async function step(who, message) {
  const signal = new AbortController().signal;
  const input = { agent: who, messages: [message], signal };
  // Dispatch through the actual Cordis waterfall. Its listener ordering is part
  // of the host contract and must not be approximated by a test implementation.
  return (
    await ctx.waterfall("agent/pre-step", input, async () => ({
      kind: "continue",
      messages: [message],
    }))
  ).messages;
}
const invoked = (messages) => messages.filter((m) => m.source?.kind === "skill-invocation");
try {
  await check("User-only registry policy", async () => {
    const skills = await ctx.skills.list();
    assert.equal(skills.length, 1);
    assert.equal(isModelInvocable(skills[0]), false);
    assert.equal(isUserInvocable(skills[0]), true);
    await assert.rejects(
      () =>
        toolMap
          .get("skill")
          .execute({ name: "vibelens" }, { agent: first, signal: new AbortController().signal }),
      /not available for model invocation/u,
    );
  });
  await check("Native explicit invocation and real resource paths", async () => {
    const messages = invoked(await step(first, user("/vibelens Build a file-sharing app")));
    assert.equal(messages.length, 1);
    const text = messages[0].content.map((item) => item.text).join("\n");
    assert.match(text, /Confirm intent and development mode/u);
    assert.match(text, /harness-chat-a/u);
    assert.match(text, /project-a/u);
    const skill = await ctx.skills.get("vibelens");
    assert.equal(
      await readFile(path.join(skill.resourceBase.path, "scripts/bo.py"), "utf8").then(
        (s) => s.length > 0,
      ),
      true,
    );
    assert.equal(
      await readFile(
        path.join(skill.resourceBase.path, "assets/stategraph-viewer/viewer.js"),
        "utf8",
      ).then((s) => s.length > 0),
      true,
    );
  });
  await check("Other conversations and quoted examples stay inactive", async () => {
    for (const text of [
      "Build a file-sharing app",
      "Example: /vibelens hello",
      "> /vibelens hello",
      "```\n/vibelens hello\n```",
      "/vibelens-other hello",
    ]) {
      assert.equal(invoked(await step(second, user(text))).length, 0, text);
    }
    assert.equal(invoked(await step(second, user("/vibelens hello", "tool-result"))).length, 0);
  });
  await check("Independent host identities", async () => {
    const messages = invoked(await step(second, user("/vibelens Focus the download path")));
    const text = JSON.stringify(messages);
    assert.match(text, /harness-chat-b/u);
    assert.doesNotMatch(text, /harness-chat-a/u);
  });
  await check("Abort propagation and registration disposal", async () => {
    const controller = new AbortController();
    controller.abort();
    await assert.rejects(() => ctx.skills.get("vibelens", { signal: controller.signal }));
  });
} finally {
  await registryFiber.dispose();
}
const out = path.join(root, ".validation/harness-runtime.json");
await mkdir(path.dirname(out), { recursive: true });
await writeFile(
  out,
  JSON.stringify(
    {
      valid: true,
      harness: "0.2.2-rc.1",
      checks,
      boundary:
        "Real registry and native invocation consumer; fixture sessions, no LLM application trial.",
    },
    null,
    2,
  ) + "\n",
);
console.log(JSON.stringify({ valid: true, checks }));
