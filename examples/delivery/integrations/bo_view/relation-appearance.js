/** Shared visual grammar: hue identifies layers, dashes separate node types,
 * and the stroke profile/head describe the relationship. None imply execution.
 */
import { t } from "./i18n.js";
import { visualType } from "./graph-classification.js";
export const relationFamilies = {
  execution: {
    label: t("Call / value transfer"),
    stroke: "single",
    width: 1,
    dash: [],
    arrow: "open",
  },
  flow: { label: t("Flow / transition"), stroke: "single", width: 1.3, dash: [], arrow: "filled" },
  condition: {
    label: t("Condition / constraint"),
    stroke: "bordered",
    width: 1,
    dash: [],
    arrow: "diamond",
  },
  reference: {
    label: t("Mapping / reference"),
    stroke: "double",
    width: 1,
    dash: [],
    arrow: "open",
  },
  containment: { label: t("Containment"), stroke: "single", width: 0.8, dash: [], arrow: "none" },
  synchronization: {
    label: t("Join / resource"),
    stroke: "double",
    width: 1,
    dash: [],
    arrow: "bar",
  },
  indirect: { label: t("Indirect path"), stroke: "bordered", width: 1, dash: [], arrow: "open" },
};

export const differentTypeDash = [9, 5];

/** Compare the displayed icon types, not storage kinds or layer membership.
 * Folding changes the visible endpoints only; original relation IDs survive.
 * Without an index, legends show a same-type example. Missing indexed nodes
 * remain explicitly unknown, rather than claiming a same-type relationship.
 */
export function endpointAppearance(edge, nodes) {
  const source = nodes?.get(edge.from),
    target = nodes?.get(edge.to);
  const sourceType = source ? visualType(source.node || source) : null;
  const targetType = target ? visualType(target.node || target) : null;
  const sameType = sourceType && targetType ? sourceType === targetType : null;
  return {
    sourceType,
    targetType,
    sameType,
    dash: edge.guide || (nodes && sameType !== true) ? differentTypeDash : [],
  };
}

export function relationFamily(type, edge = {}) {
  if (type === "indirect") return "indirect";
  if (["contains", "code-contains", "code-defines", "code-parameter"].includes(type))
    return "containment";
  if (
    [
      "guard",
      "declares_guard",
      "guarded_by",
      "guard_resolves_decision",
      "transition_guarded_by",
      "decision_reads_fact",
      "decision_result",
    ].includes(type)
  )
    return "condition";
  if (
    [
      "flow",
      "transition",
      "declares_event",
      "declares_effect",
      "requests_transition",
      "has_effect",
      "declares_target",
      "action_requests_event",
      "transition_has_effect",
    ].includes(type)
  )
    return "flow";
  if (["resource", "join"].includes(type)) return "synchronization";
  if (
    [
      "maps",
      "references",
      "shared",
      "code-maps",
      "code-links",
      "code-imports",
      "code-exports",
      "code-dependency",
      "code-inherits",
      "describes_fact",
      "state_subject",
      "other",
    ].includes(type) ||
    (edge.members || [edge]).every((member) => member.origin === "capture-field")
  )
    return "reference";
  if ((edge.members || [edge]).every((member) => member.evidence_kind === "conceptual"))
    return "reference";
  return "execution";
}

/** Wireframe heads lie on the link's plane and use the same vocabulary as 2D.
 * Filled heads are instanced cones; hollow heads stay in the batched line buffer.
 */
export function headSegments(kind) {
  if (kind === "open")
    return [
      [
        [-1, -0.5],
        [0, 0],
      ],
      [
        [0, 0],
        [-1, 0.5],
      ],
    ];
  if (kind === "diamond")
    return [
      [
        [0, 0],
        [-0.6, -0.45],
      ],
      [
        [-0.6, -0.45],
        [-1.2, 0],
      ],
      [
        [-1.2, 0],
        [-0.6, 0.45],
      ],
      [
        [-0.6, 0.45],
        [0, 0],
      ],
    ];
  return kind === "bar"
    ? [
        [
          [0, -0.6],
          [0, 0.6],
        ],
      ]
    : [];
}
