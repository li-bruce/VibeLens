import { machineProjection } from "./machine-projection.js";
import { captureFields } from "./capture-fields.js";
import { t as boTranslate } from "./i18n.js";

export function stateNodeId(model, value) {
  return model.nodes.find((n) => n.kind === "state" && n.value === value)?.id || "state." + value;
}
/** Assemble every semantic layer before filtering, folding or rendering.
 * Both 2D and 3D use these exact IDs and original edge endpoints. Runtime facts
 * annotate declarations; absence of an event never becomes a synthetic success.
 */
export function graphInventory(
  view,
  { attempt, choice = "latest", step = "latest", memberships = [] } = {},
) {
  const all = new Map(view.model.nodes.map((n) => [n.id, n])),
    rawEdges = [...view.model.edges];
  for (const n of view.model.nodes) {
    if (n.kind === "state") continue;
    const captures = captureFields(n);
    for (const field of captures.nodes) all.set(field.id, field);
    rawEdges.push(...captures.edges);
  }
  const machine = machineProjection(view.model, view.machine, { attempt, choice, step });
  for (const node of machine.nodes) all.set(node.id, node);
  rawEdges.push(...machine.edges);
  // Membership is a view reference to one canonical identity, not another call.
  for (const m of memberships) {
    const member = all.get(m.member),
      group = all.get(m.group);
    if (!member || !group || member.parent === group.id || member.id === group.id) continue;
    const id = "ref:" + encodeURIComponent(group.id) + ":" + encodeURIComponent(member.id);
    all.set(id, {
      ...member,
      id,
      parent: group.id,
      referenceOf: member.id,
      event_node: member.event_node || member.id,
      summary: boTranslate("Shared entry: ") + m.reason,
      origin: "membership-reference",
      membership: m,
    });
    rawEdges.push({
      id: "shared:" + id,
      from: id,
      to: member.id,
      type: "shared",
      label: boTranslate("Same node"),
      evidence: m.evidence,
    });
  }
  return { all, rawEdges };
}
