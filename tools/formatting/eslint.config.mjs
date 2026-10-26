/** Owned browser/native sources only; vendor and generated files are immutable. */
import globals from "globals";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const scope = JSON.parse(fs.readFileSync(path.join(root, "tools/source-scope.json"), "utf8"));
const rules = {
  "no-undef": "error",
  "no-unreachable": "error",
  "valid-typeof": "error",
  "constructor-super": "error",
  "no-async-promise-executor": "error",
  "no-dupe-args": "error",
  "no-dupe-class-members": "error",
  "no-dupe-keys": "error",
  "no-unsafe-finally": "error",
  "no-constant-binary-expression": "error",
  "no-unused-vars": ["error", { args: "none", caughtErrors: "none", ignoreRestSiblings: true }],
  "eqeqeq": ["error", "always", { null: "ignore" }],
};
export default [
  { ignores: scope.exclude },
  {
    files: scope.javascript,
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: { ...globals.browser, ...globals.worker, PIXI: "readonly", ELK: "readonly" },
    },
    rules,
  },
  {
    files: ["skills/vibelens/scripts/bo_observer/adapters/javascript/*.mjs"],
    languageOptions: { globals: { ...globals.browser, ...globals.node } },
  },
];
