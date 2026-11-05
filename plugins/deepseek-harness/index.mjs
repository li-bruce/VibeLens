/**
 * Register the packaged VibeLens skill with DeepSeek Harness.
 *
 * The host owns user-message parsing and per-session instruction injection. This
 * provider only supplies a complete, explicitly invoked skill. It starts no
 * servers and rewrites no workspace files. Its injection hook only handles
 * host-generated VibeLens invocations in the requesting session.
 */
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

export const name = "vibelens";
export const inject = ["skills", "workingDirectory"];
const providerName = "vibelens-package";
const directory = fileURLToPath(new URL("./skill/", import.meta.url));
const instructionPath = fileURLToPath(new URL("./skill/SKILL.md", import.meta.url));

/** Load metadata lazily so a missing/incomplete artifact fails discovery clearly. */
async function definition(signal) {
  const raw = await readFile(instructionPath, { encoding: "utf8", signal });
  const header = /^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/u.exec(raw);
  const description = header?.[1].match(/^description: (.+)$/mu)?.[1];
  if (!header || !/^name: vibelens$/mu.test(header[1]) || !description) {
    throw new Error("VibeLens package has an invalid skill entrypoint.");
  }
  return { description, content: raw.slice(header[0].length).trim() };
}

/** Register one provider; Cordis disposes it with this plugin's own lifecycle. */
export function apply(ctx) {
  ctx.skills.registerProvider(() => ({
    name: providerName,
    async list(options = {}) {
      const { description } = await definition(options.signal);
      return [
        {
          name,
          description,
          path: instructionPath,
          invocation: { modelInvocable: false, userInvocable: true },
          provider: providerName,
          source: "bundled",
          rank: 600,
          resourceBase: { kind: "directory", path: directory },
          locator: instructionPath,
        },
      ];
    },
    async get(candidate, options = {}) {
      // Load only our registered entry. A caller cannot turn a locator into an
      // arbitrary file read or silently substitute another skill's identity.
      if (candidate.name !== name || candidate.locator !== instructionPath) return undefined;
      const { description, content } = await definition(options.signal);
      const { locator: _locator, rank: _rank, ...summary } = candidate;
      return {
        ...summary,
        description,
        invocation: { modelInvocable: false, userInvocable: true },
        content:
          `${content}\n\n## DeepSeek Harness host binding\n\n` +
          "This skill was explicitly loaded by the host from the user's /vibelens gesture. " +
          "Treat that gesture as the explicit activation equivalent of $vibelens for this conversation and project. " +
          "Follow the same development, confirmation, mapping and verification workflow. " +
          "Resolve relative references and scripts under the resource directory supplied by the host. " +
          "For activation and manual viewer controls, preserve the original /vibelens message and pass --host deepseek-harness with the actual host conversation ID in --conversation. " +
          "If the host does not expose that identity, leave conversation controls pending; the local Web viewer and ordinary development workflow remain available. " +
          "Never reuse another chat's ID or create a global activation file.",
      };
    },
  }));
  // Only augment a host-generated explicit skill injection. Ordinary chats,
  // quoted slash examples and model tool results gain no VibeLens instructions.
  ctx.on(
    "agent/pre-step",
    async ({ agent, messages, signal }, next) => {
      const decision = await next();
      if (decision.kind === "reject") return decision;
      const isInvocation = (message) =>
        message.source?.kind === "skill-invocation" && message.source.name === name;
      if (!decision.messages?.some(isInvocation)) return decision;
      const explicitlyRequested = messages.some(
        (message) =>
          message.source?.kind === "user" &&
          message.content?.some(
            (block) => block.type === "text" && /^\s*\/vibelens(?:\s|$)/u.test(block.text),
          ),
      );
      // Harness recognizes slash tokens within prose too. VibeLens deliberately
      // requires the user's leading gesture, preserving the explicit-only policy.
      if (!explicitlyRequested)
        return {
          ...decision,
          messages: decision.messages.filter((message) => !isInvocation(message)),
        };
      if (typeof agent.id !== "string" || !/^[A-Za-z0-9_-]{1,160}$/u.test(agent.id)) {
        throw new Error("VibeLens requires the actual Harness session identity.");
      }
      const cwd = await ctx.workingDirectory.ensure(agent, signal);
      const binding = JSON.stringify({ host: "deepseek-harness", conversation: agent.id, cwd });
      return {
        ...decision,
        messages: decision.messages.map((message) =>
          isInvocation(message)
            ? {
                ...message,
                content: [
                  ...message.content,
                  { type: "text", text: `VibeLens host context: ${binding}` },
                ],
              }
            : message,
        ),
      };
    },
    { prepend: true },
  );
}
