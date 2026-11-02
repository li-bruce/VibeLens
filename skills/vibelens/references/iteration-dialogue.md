# Confirm a later change in the existing graph

Use this for subsequent development turns in an explicitly activated VibeLens conversation. Keep the current project's drive/observe choice, confirmed decisions and stable graph identities. A normal business change request starts this workflow; `/vibelens` remains the prefix for manual viewer controls.

## Before changing behavior

1. Run the project-local `change_sync.py recall --root PROJECT`. Read the current request, accepted decisions and affected layer/source summary. Continue an open change record; otherwise record the actual request with `begin` and its allowed requirement changes.
2. Relate the user's words to existing business node IDs, relevant state/rule nodes and incoming/outgoing dependencies. Briefly say which part changes and why. Keep new implementation details in coding; ask the user about unresolved business meaning only.
3. Update a candidate `discovery.json` from the current intent. Preserve original sources and decisions. A new or contradictory interpretation becomes a focused question tied to affected IDs. Reuse exact answers already explicit in the conversation. Record changed decisions in `changes` with the complete previous decision and actual change source.
4. Show the proposed local business network in the conversation and provide the verified live graph URL. State the changed condition, step or connection in one short sentence. Include nearby dependencies or explicit boundaries; do not redraw the entire project. Use the same stable IDs in both views:

   ```text
   python SKILL/scripts/bo_design.py preview --root PROJECT --nodes AFFECTED_ID NEIGHBOR_ID --url ACTUAL_GRAPH_URL --out review/change-preview.md
   ```

   `--nodes` uses the existing or reserved primary graph IDs. Use `bo_design.py focus` to highlight that region. This internal workflow focus follows the current development request; it does not authorize unrelated manual viewer changes. The draft is a declaration, with no invented execution values.
5. Confirm newly interpreted business meaning before implementing it. An explicit user instruction or previous confirmation can authorize the exact matching change; do not ask for the same decision again. If something remains ambiguous, ask the smallest useful question and retain pending status until answered. A partial answer resolves only its part. Opening Web, silence and graph notes do not answer a business question.

An example exchange:

> User: Let me withdraw a shared file. What happens to links I already sent?
>
> Assistant: This affects **Share file → Download file**. Should withdrawing a share also stop downloads through the links already sent?
>
> User: Yes. After withdrawal those links must stop working.
>
> Assistant: The updated region is **Share file → Active link → Withdrawn link**; downloads require an active link. Here is the local graph and its Web URL.

This resolves the stated uncertainty. It adds no expiration policy, notification rule or role beyond the user's request.

## During and after coding

Maintain the declaration, actual execution or observation adapters, source/function/parameter bindings, probes and independent cases through the existing coding workflow. A source-only refactor retains the business network and its IDs; reconcile implementation details without reopening business decisions.

Run scan, inspect, verify, accept and check. Show the resulting local graph and briefly identify what changed. Report implementation mapping, state constraints, business rules and project checks separately. The user discusses intent and examines the graph; the agent maintains the intermediate files.

Use [requirements dialogue](requirements-dialogue.md) for history and question records, [conversation and graph](conversation-web.md) for the preview, and [continuous development](continuous-development.md) for the coding gates. These scripts validate recorded decisions and mappings. They do not understand arbitrary user prose or prove that a coding agent followed every conversational instruction.
