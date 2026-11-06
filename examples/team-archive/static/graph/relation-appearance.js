/** Shared visual grammar. Hue encodes layer; stroke and head encode relationship. */
import { t } from "./i18n.js";
export const relationFamilies = {
  execution: { label: t("Call / value transfer"), dash: [], arrow: "open" },
  flow: { label: t("Flow / transition"), dash: [10, 5], arrow: "filled" },
  condition: { label: t("Condition / constraint"), dash: [2, 5], arrow: "diamond" },
  reference: { label: t("Mapping / reference"), dash: [9, 3, 2, 3], arrow: "open" },
  containment: { label: t("Containment"), dash: [1, 5], arrow: "none" },
  synchronization: { label: t("Join / resource"), dash: [6, 3], arrow: "bar" },
  indirect: { label: t("Indirect path"), dash: [2, 4, 8, 4], arrow: "open" },
};

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
