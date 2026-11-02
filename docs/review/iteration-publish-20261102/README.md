# Later-turn dialogue and test publication

The existing implementation already supports later-turn recall, questions tied to graph IDs, recorded answers and change history, local graph previews, and acceptance gates that reject stale or removed decisions. This round makes the before-coding sequence explicit in the Skill and links its existing mechanisms together.

The workflow is: restore confirmed context → identify the affected graph region and boundaries → show the proposed local graph → resolve changed meaning → maintain code/declarations/probes → verify and show the result. Explicit confirmations are reused; source-only refactors retain business meaning and avoid repeat questioning. Web continues to display the graph while the user answers in the development conversation.

## Scope and evidence

- [Iteration guidance](../../../skills/vibelens/references/iteration-dialogue.md) and the main Skill entrypoint now state this later-turn sequence.
- [Seven regression cases](../../../tests/test_iteration_dialogue.py) exercise existing requirements/discovery APIs, actual local previews and both CLI entrypoints. They check that only the new question is asked, pending questions are not repeated, answers update the affected region, unrelated branches and IDs survive, changed decisions need source/history, and confirmed meaning can be reused.
- These are scripted synthetic records and actual script/API tests. They are not a new human dialogue or an independent LLM trial.
- The prior [complete relation-insertion acceptance](../relation-insertion-20261102/README.md) includes the full original gate, native execution preservation and managed runtime parity. This publication also rechecks the complete current snapshot and its clean Git export.

The current test ref is documented in the [test instructions](../../releases/2026-11-02-test.md). Native engines, business rules and old verification requirements remain unchanged in this round.

## Final checks

- [Complete release gate](full-gate.json): `tools/verify.py --database` passed on 2026-11-02, 08:26:50–08:33:03 UTC. All earlier checks remain in place.
- [Final iteration cases](iteration-dialogue.json): seven cases passed after the [test-fixture review correction](review-correction.md). The newly requested withdrawal action and its relation now have explicit assertions, alongside preservation of previous IDs and the unrelated message branch.
- [Existing dialogue cases](requirements-dialogue.json): 22 cases passed. [Document links](document-links.json) passed too.
- [Source quality](source-quality-report.json): 133 maintained Python and 94 JavaScript modules passed syntax/lint/format checks.
- [Clean Git export](clean-export-report.json): both frozen examples passed from the staged Git export without regeneration or reapproval.
- [Clean Skill installation](clean-install.json): six checks passed using only the staged Skill and installer in an isolated project, including the installed relation CLI and later-turn local preview.
- [Final acceptance summary](acceptance.json) records checked subtree identities so later publication metadata cannot be mistaken for a runtime change.

The raw CRLF logs and frozen receipts retain their original bytes. Their scoped Git attributes allow those recorded line endings; maintained source remains covered by its existing format/lint gates. The schema attribute still checks real trailing blanks while recognizing CRLF. Earlier whitespace findings are retained in the review records.
