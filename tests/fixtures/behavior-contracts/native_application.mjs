/** Native file-backed fixture. Business functions have no observer dependency. */
import { readFile, writeFile, rename } from "node:fs/promises";
import { createHash } from "node:crypto";

/** Stage a grant change after the caller's asynchronous permission check.
 * @param {string} path Native store file.
 * @param {boolean} allowed Current permission decision.
 */
export async function share(path, allowed) {
  await new Promise((resolve) => setImmediate(resolve));
  if (!allowed) throw new Error("Permission denied");
  const state = await read_native(path);
  state.grant = "active";
  await writeFile(path + ".pending", JSON.stringify(state));
}

/** Replace the store with the staged native result. */
export async function commit(path) {
  await rename(path + ".pending", path);
}

/** Read values from the authoritative file independently of observations. */
export async function read_native(path) {
  return JSON.parse(await readFile(path, "utf8"));
}

/** Read the committed bytes for this invocation's completion witness. */
export async function read_commit(path) {
  return createHash("sha256").update(await readFile(path)).digest("hex");
}
