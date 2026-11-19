/**
 * Node transport reader for revision-pinned project artifacts.
 * Python owns complete cross-model definition validation; native executors still
 * validate their supported machine semantics. This reader does not grant binding
 * or runtime acceptance and never executes a behavior expression.
 */
import { readFile, realpath, access } from "node:fs/promises";
import path from "node:path";
import { createHash } from "node:crypto";
import { bo_parseJson } from "./bo_json.mjs";

const hash = (raw) => createHash("sha256").update(raw).digest("hex");
const versions = {
  discovery: new Set(["business-discovery/v1", "business-discovery/v2", "business-discovery/v3"]),
  behavior: new Set(["bo-behavior/v1"]),
  analysis_profiles: new Set(["bo-analysis-profile/v1"]),
};
const fail = (code) => {
  throw new Error(code);
};

function fields(value, required) {
  if (
    !value ||
    typeof value !== "object" ||
    Array.isArray(value) ||
    Object.keys(value).length !== required.length ||
    required.some((key) => !Object.hasOwn(value, key))
  )
    fail("project_fields");
}

async function contained(root, name) {
  if (
    typeof name !== "string" ||
    !name ||
    /[\\:]/.test(name) ||
    name.split("/").some((part) => !part || part === "." || part === "..")
  )
    fail("artifact_path");
  const full = await realpath(path.join(root, name));
  const relative = path.relative(root, full);
  if (relative.startsWith(".." + path.sep) || relative === ".." || path.isAbsolute(relative))
    fail("artifact_path");
  return full;
}

async function noPendingMigration(root) {
  try {
    await access(path.join(root, ".stategraph/migrations/active.json"));
  } catch (error) {
    if (error.code === "ENOENT") return;
    throw error;
  }
  fail("migration_pending");
}

export async function bo_readProject(root, filename = "bo_stategraph/project.json") {
  const base = await realpath(root);
  await noPendingMigration(base);
  const file = await contained(base, filename);
  const raw = await readFile(file);
  const project = bo_parseJson(raw);
  if (!["bo-project/v1", "bo-project/v2"].includes(project.protocol)) fail("project_version");
  fields(project, [
    "protocol",
    "project_id",
    "selection",
    "model",
    ...(project.protocol === "bo-project/v2" ? ["contracts"] : []),
  ]);
  fields(project.selection, ["mode", "source", "answer", "locator"]);
  if (
    !["drive", "observe"].includes(project.selection.mode) ||
    project.selection.source !== "user" ||
    [project.project_id, project.selection.answer, project.selection.locator].some(
      (value) => typeof value !== "string" || !value.length,
    )
  )
    fail("project_selection");
  if (
    !project.model ||
    (project.model.project_id !== undefined && project.model.project_id !== project.project_id)
  )
    fail("project_mismatch");
  const fingerprints = new Map([[file, hash(raw)]]);
  const documents = {};
  if (project.protocol === "bo-project/v2") {
    fields(project.contracts, ["discovery", "behavior", "analysis_profiles"]);
    if (!Array.isArray(project.contracts.analysis_profiles)) fail("project_fields");
    if (project.contracts.behavior && !project.contracts.discovery) fail("missing_discovery");
    const names = new Set();
    for (const [role, configured] of Object.entries(project.contracts)) {
      const refs =
        role === "analysis_profiles" ? configured : configured === null ? [] : [configured];
      for (const ref of refs) {
        fields(ref, ["path", "sha256", "schema"]);
        if (!/^[0-9a-f]{64}$/.test(ref.sha256) || !versions[role].has(ref.schema))
          fail("unsupported_artifact_version");
        if (names.has(ref.path)) fail("duplicate_artifact_path");
        names.add(ref.path);
        const source = await contained(base, ref.path);
        const payload = await readFile(source);
        if (hash(payload) !== ref.sha256) fail("artifact_revision_mismatch");
        const value = bo_parseJson(payload);
        if (value.schema !== ref.schema) fail("artifact_version_mismatch");
        if (
          role !== "analysis_profiles" &&
          value.project_id !== project.project_id &&
          !(
            role === "discovery" &&
            value.schema === "business-discovery/v1" &&
            value.project_id === undefined
          )
        )
          fail("project_mismatch");
        fingerprints.set(source, ref.sha256);
        if (role === "analysis_profiles") (documents[role] ??= []).push(value);
        else documents[role] = value;
      }
    }
    if (project.contracts.analysis_profiles.length && !project.contracts.behavior)
      fail("missing_behavior");
  }
  for (const [name, expected] of fingerprints)
    if (hash(await readFile(name)) !== expected) fail("artifacts_changed_during_read");
  await noPendingMigration(base);
  return { project, documents, definitionValidation: "requires_observer_check" };
}
