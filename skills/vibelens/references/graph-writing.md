# Writing for developers

Use this prompt when drafting or revising graph labels, module summaries and demonstrations:

> Write for a developer trying to understand this application's behavior. Name the action, object, condition or source symbol directly. Keep the values, relationships and source locations that explain a result. Remove repeated labels, generic praise, authoring notes and statements about how completely the graph was generated. Write locale-specific explanations and retain exact source identifiers. Each sentence must help the reader identify a behavior, understand a decision or locate its implementation.

## Graph content

- Maintain both source names and short explanations. The viewer's **Semantic labels** switch is on by default; switching it off shows lexical symbols, captured field keys, native schema names, state values and relation types/triggers. Keep source bindings exact. A collected field keeps its own key, not its collection owner's function name.
- Each node and edge retains its unique ID. Explanations are a display overlay keyed by that ID; every endpoint, source binding, cross-layer link and recorded reference keeps the original identity. Equal display names do not merge elements. Never use an explanation as an identity or relationship lookup key.
- Put AI explanations in `model.presentation.names`: `nodes` and `edges` map exact IDs to labels; `states` maps state values and `events` maps transition triggers. Use locale maps such as `{ "en": "Sign in", "zh-CN": "登录" }` for maintained explanations. Prepare English and Chinese aliases when maintaining the affected nodes, edges, states and events. The interface selects its own language; it never substitutes an explanation in the other language. Legacy single-language labels remain compatible in that language. Missing translations retain the exact source name until the next maintenance pass. Use 1–60 characters, one line, preferably 2–6 words. `nodes` can address generated field IDs such as `field:login:out:allowed`. Preserve these maps when generating or merging layers. Existing `label` values are the compatibility fallback; absent explanations keep their source name.
- Explain the specific action, condition, value or result: `Verify password`, `May download`, `Remaining slots`, `Waiting for review`. Omit “actual structure”, “complete mapping”, “collected field” and similar authoring language. Use the confirmed business meaning and current source; ask about an ambiguity instead of inventing a meaning. Recheck affected explanations when behavior, source mappings or field meaning changes. Explanations never rename an executable state, change an assertion or turn a static relation into an observed transfer.

- A label names the element: `Revoke access`, `recipient_id`, `SharingService.revoke` or `shares`. A summary adds a specific input, condition or effect only when the label leaves it unclear.
- Keep business captions to a short action and object. Put actor restrictions and permission conditions on the related rule nodes or in the summary. The viewer wraps captions to measured bounds; preserve the complete meaning and exact source name for inspection.
- A concrete API node names its registered HTTP method and path and links to its actual handler. A generic GET/POST capture wrapper belongs to execution/collection detail. Keep real catch-all route templates explicit; preserve route, handler and capture identities rather than merging them by shared names. Connect them to user operations through verified mappings.
- Read concise API/function/parameter explanations from their source documentation, retaining path and declaration evidence. Use localized presentation aliases for short names and keep source comments available for inspection. Follow [source documentation](source-documentation.md); missing comments remain an explicit gap.
- Keep business conditions such as “Only the owner can revoke access.” Preserve observed errors, unknown values and stale-evidence indicators; they explain what the developer can conclude.
- Put collection scope, mapping coverage and verification results in diagnostics or review reports. Phrases such as “actual inputs and outcomes”, “configuration scope complete” and “implementation ownership” do not explain an application node.
- Name edges by their actual meaning. Captured fields belong to an event; they are not automatically function arguments or observed value transfers. Retain relation types and evidence distinctions.
- Shorten display text through presentation labels. Preserve IDs, state values, source symbols, bindings and raw recording/evidence content. Use advanced inspection for provenance and analysis details.

| Draft | Display |
|---|---|
| Upload file: actual inputs and outcomes from the running application | Upload file |
| Actual structure · configuration scope complete | SQLite |
| Canonical declaration state: private | Private |
| Revoke recipient access | Revoke access — keep the function and `recipient_id` visible when inspecting it |

## Demonstration stories

Organize a demo around the reader's decisions, rather than every action taken during development. A useful sequence is: confirm the flow → record a problem → inspect a focused path → ask AI to repair it → verify the next run. Combine repeated exploration and view editing into the inspection step.

Show the development conversation where requirements or code change. Show recording, filtering and source exploration as interactions with VibeLens. One short explanation and a concrete interaction usually suffice for a step. Keep the full scripted dialogue, deliberately seeded defects and test provenance in linked review material.

Before delivery, read only the visible labels and story in order. Remove any sentence that repeats a heading or describes the generator instead of the application. Check that the remaining text still explains the business conditions, observed result and route into source.
