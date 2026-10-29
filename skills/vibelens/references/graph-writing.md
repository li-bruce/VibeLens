# Writing for developers

Use this prompt when drafting or revising graph labels, module summaries and demonstrations:

> Write for a developer trying to understand this application's behavior. Name the action, object, condition or source symbol directly. Keep the values, relationships and source locations that explain a result. Remove repeated labels, generic praise, authoring notes and statements about how completely the graph was generated. Use the user's language for explanations and retain exact source identifiers. Each sentence must help the reader identify a behavior, understand a decision or locate its implementation.

## Graph content

- A label names the element: `Revoke access`, `recipient_id`, `SharingService.revoke` or `shares`. A summary adds a specific input, condition or effect only when the label leaves it unclear.
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
