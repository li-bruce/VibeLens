/** Select one recorded subject without confusing equal values in different models.
 * Explicit node identities win. A model-qualified state requires matching model
 * ownership; value-only matching remains available only for the archived,
 * unqualified single-model case. This function never infers execution from a link.
 */
export function preparedNodeActive(node, step) {
  if (!step || !node.id) return false;
  if (node.id === step.node) return true;
  if (step.state_id !== undefined) return node.id === step.state_id;
  if (node.value === undefined || node.value !== step.state) return false;
  if (node.state_model_id !== undefined || step.state_model_id !== undefined) {
    return typeof node.state_model_id === "string" && node.state_model_id === step.state_model_id;
  }
  return true;
}
