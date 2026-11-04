/** Typed design relationships remain inspectable before and after source binding.
 * These links describe a model. Runtime evidence is tracked separately by event
 * identities; drawing a dependency never turns it into an observed call.
 */
export const conceptRelations = Object.freeze({
  describes_fact: "Describes fact",
  state_subject: "State of",
  declares_event: "Event",
  declares_guard: "Guard",
  declares_effect: "Effect",
  requests_transition: "Requests transition",
  guarded_by: "Guarded by",
  has_effect: "Has effect",
  declares_target: "Target state",
  decision_result: "Decision result",
  guard_resolves_decision: "Uses decision",
  action_requests_event: "Requests event",
  transition_guarded_by: "Guarded by",
  decision_reads_fact: "Reads fact",
  transition_has_effect: "Has effect",
});
export const conceptRelationTypes = Object.keys(conceptRelations);
