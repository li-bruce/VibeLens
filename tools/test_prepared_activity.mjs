/** Equal-valued states in independent models must remain distinct on replay. */
import assert from "node:assert/strict";
import { preparedNodeActive } from "../docs/site/case-activity.mjs";

const grant = { id: "native_state:grant:active", state_model_id: "grant", value: "active" };
const session = { id: "native_state:session:active", state_model_id: "session", value: "active" };
const event = { node: "share_file", state_model_id: "grant", state: "active" };
assert.equal(preparedNodeActive(grant, event), true);
assert.equal(
  preparedNodeActive(session, event),
  false,
  "A grant does not activate a login session",
);
assert.equal(
  preparedNodeActive(grant, { node: "logout", state: "active" }),
  false,
  "An unqualified state cannot identify one model in a forest",
);
assert.equal(preparedNodeActive(grant, { state_model_id: "grant", state: "inactive" }), false);
assert.equal(
  preparedNodeActive(grant, { node: grant.id }),
  true,
  "The original node ID remains authoritative",
);
assert.equal(preparedNodeActive({ id: "share_file" }, event), true);
assert.equal(preparedNodeActive(grant, null), false);
assert.equal(preparedNodeActive({}, undefined), false);

const legacy = { id: "state_active", value: "active" };
assert.equal(
  preparedNodeActive(legacy, { state: "active" }),
  true,
  "The archived single-model teaching case retains its existing behavior",
);
assert.equal(
  preparedNodeActive(legacy, event),
  false,
  "A qualified event cannot be borrowed by an unqualified state",
);
assert.equal(
  preparedNodeActive(grant, { state_id: session.id, state: "active", state_model_id: "grant" }),
  false,
  "An explicit different identity cannot fall through to a value match",
);
assert.equal(preparedNodeActive(session, { state_id: session.id }), true);

console.log(
  "PASS: prepared activity retains qualified model identity and legacy single-model compatibility",
);
