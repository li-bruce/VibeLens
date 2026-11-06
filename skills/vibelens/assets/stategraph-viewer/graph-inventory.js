import { machineProjection } from "./machine-projection.js";
import { captureFields } from "./capture-fields.js";
import { t as boTranslate } from "./i18n.js";
import { nameNode, explainedName, declaredEdges } from "./graph-names.js";
import { annotateConcepts } from "./concept-observation.js";
import { applyConceptContainment } from "./concept-containment.js";
import { validateEquivalentRelations } from "./edge-identities.js";

export function stateNodeId(model, value) {
  return model.nodes.find((n) => n.kind === "state" && n.value === value)?.id || "state." + value;
}

/** Canonical ancestry for controls; display projections may detach containers. */
const declarationCache = new WeakMap();
export function declarationNodes(view) {
  const prior = declarationCache.get(view),
    signature = [
      view.model.nodes,
      view.concept_structure?.nodes,
      view.concept_structure?.edges,
      view.concept_structure?.revision,
      view.concept_structure?.stage,
    ];
  if (prior && signature.every((value, index) => prior.signature[index] === value))
    return prior.nodes;
  const declared = new Map((view.concept_structure?.nodes || []).map((node) => [node.id, node]));
  for (const native of view.model.nodes) {
    const concept = declared.get(native.id);
    // A shared identity keeps native capture/state authority while retaining
    // inspectable semantic metadata. Never replace source, kind or lifecycle.
    declared.set(
      native.id,
      concept?.concept_definition
        ? {
            concept_kind: concept.concept_kind,
            concept_definition: concept.concept_definition,
            concept_id: concept.concept_id || concept.id,
            concept_layer: concept.layer,
            ...native,
            ...(concept.layer === "business" && native.layer === "business" && concept.parent
              ? { parent: concept.parent, containment_kind: "business_decomposition" }
              : {}),
            ...(concept.layout_routes ? { layout_routes: concept.layout_routes } : {}),
            // The confirmed conceptual name is a display overlay. Native
            // source, capture registration and lifecycle still own this ID.
            concept_label: concept.label,
          }
        : native,
    );
  }
  const nodes = annotateConcepts(view, [...declared.values()]);
  declarationCache.set(view, { signature, nodes });
  return nodes;
}
/** Assemble every semantic layer before filtering, folding or rendering.
 * Both 2D and 3D use these exact IDs and original edge endpoints. Runtime facts
 * annotate declarations; absence of an event never becomes a synthetic success.
 */
export function graphInventory(
  view,
  { attempt, choice = "latest", step = "latest", memberships = [] } = {},
) {
  // A bound concept projection carries the same design identities into runtime.
  // Actual model nodes win a collision; the overlay is never an executor or a
  // reason to borrow a physical function's lifetime.
  const all = new Map(declarationNodes(view).map((node) => [node.id, node])),
    rawEdges = [
      ...new Map(
        [...(view.concept_structure?.edges || []), ...view.model.edges].map((e) => [e.id, e]),
      ).values(),
    ];
  // Naming overlays add UI fields; validate the untouched assertions instead.
  validateEquivalentRelations([
    ...new Map(
      [...(view.concept_structure?.edges || []), ...declaredEdges(view.model)].map((e) => [
        e.id,
        e,
      ]),
    ).values(),
  ]);
  for (const original of [...all.values()]) {
    const n = nameNode(original, view.model, view.manifest?.bindings);
    all.set(n.id, n);
    if (n.kind === "state") continue;
    const captures = captureFields(n);
    for (const field of captures.nodes) all.set(field.id, field);
    rawEdges.push(...captures.edges);
  }
  const machine = machineProjection(view.model, view.machine, {
    attempt,
    choice,
    step,
  });
  for (const node of machine.nodes) all.set(node.id, { ...all.get(node.id), ...node });
  rawEdges.push(...machine.edges);
  applyConceptContainment(all, rawEdges);
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
  // Generated fields, machine states and shared references use the same policy.
  for (const [id, node] of all) all.set(id, nameNode(node, view.model, view.manifest?.bindings));
  for (let index = 0; index < rawEdges.length; index++) {
    const edge = rawEdges[index],
      explanation = explainedName(view.model.presentation?.names?.edges?.[edge.id]);
    rawEdges[index] = {
      ...edge,
      label:
        view.model.presentation?.name_mode === "source"
          ? edge.event || edge.code_relation || edge.data_relation || edge.type
          : explanation || boTranslate(edge.label || ""),
    };
  }
  return { all, rawEdges };
}
