/** Product checks use actual exported records; the old simulated app is archived. */
import assert from "node:assert/strict";
import fs from "node:fs";
import { extra, chinese } from "../docs/site/messages.mjs";
import { messages as caseMessages } from "../docs/site/case-messages.mjs";
import { messages as homeMessages } from "../docs/site/home-messages.mjs";
import { presentCase } from "../docs/site/case-copy.mjs";
await import("./test_file_story.mjs");
await import("./test_case_artifacts.mjs");

for (const version of [1, 2]) {
  const original = JSON.parse(
    fs.readFileSync(new URL(`../docs/site/case-data/v${version}.json`, import.meta.url)),
  );
  const before = structuredClone(original);
  const display = presentCase(original);
  assert.deepEqual(original, before, "Presentation cannot rewrite archived evidence");
  assert.deepEqual(display.recording.events, original.recording.events);
  assert.deepEqual(display.sources, original.sources);
  // The model remains identical after removing the sole allowed display field.
  const semantics = (model) => ({
    ...model,
    nodes: model.nodes.map(({ summary, ...node }) => node),
  });
  for (const model of ["view", "context"]) {
    const a = model === "view" ? display.view.model : display.recording.context.model;
    const b = model === "view" ? original.view.model : original.recording.context.model;
    assert.deepEqual(semantics(a), semantics(b));
    assert.ok(
      !a.nodes.some((node) =>
        /actual inputs and outcomes|configuration scope complete|Native rule predicate|Canonical declaration state:/.test(
          node.summary || "",
        ),
      ),
    );
  }
}

for (const name of ["index.html", "demo.html"]) {
  const html = fs.readFileSync(new URL("../docs/site/" + name, import.meta.url), "utf8");
  const keys = [...html.matchAll(/data-i18n(?:-aria)?="([^"]+)"/g)].map((match) => match[1]);
  for (const key of keys)
    assert.ok(
      extra[key]?.[1] || chinese[key] || caseMessages[key]?.[1] || homeMessages[key]?.[1],
      name + ": Chinese copy missing for " + key,
    );
}
for (const [key, pair] of Object.entries({
  ...extra,
  ...caseMessages,
  ...homeMessages,
})) {
  assert.equal(pair.length, 2, "Two locales required: " + key);
  assert.ok(
    pair.every((value) => typeof value === "string" && value.trim()),
    "Empty locale: " + key,
  );
}
console.log(
  "PASS: real case integrity, detached replay, dialogue separation, focused source projection and bilingual product copy.",
);
