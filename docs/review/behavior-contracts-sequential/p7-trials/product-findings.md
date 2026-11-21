# P7 product scene review

These findings concern the static walkthrough, not the application state engines.
They are collected before the product repair batch. The canonical viewer and the
native trial receipts keep their separate acceptance results.

| ID | Current source finding | Required repair and regression |
|---|---|---|
| P7-S01 | `case-confirmation-model.mjs` and `build_case_preview.py` read a single `model.machine`; the accepted trials use four entries in `model.machines`. | Build confirmation and replay scopes from model-qualified identities. Verify every declared state, including independent announcement and session models, against the selected archived epoch. |
| P7-S02 | Both `case-prepared-graph.mjs` and `case-prepared-spatial.mjs` highlight any state whose value equals `step.state`. Two models can both contain `active`. | Share a qualified activity predicate between 2D and 3D. An activity in one model must not activate an equal-valued state in another model. Retain the legacy single-model fixture explicitly. |
| P7-S03 | The current walkthrough describes the older example's seeded revoke bug and uses fixed `revoke`/`download` identities. The new trial's initial admission-time policy was confirmed and valid. | Add an evidence-bound story adapter for initial confirmation, ordinary observation, a changed permission boundary and verification. Preserve the old example's regression expectations. |
| P7-S04 | The updated ordinary Node recording admitted preparation before revocation. It therefore shows a ready task, not denied preparation. | Use that record for its actual schedule. Reference a separately retained controlled native case for denial after revocation, with its case/event/frame/SQL identities. Do not rerun to obtain a preferred order. |

Private selection inspection has verified the two accepted Node recording epochs:

- Initial: `d74073bf48ab4e3e8601c6db5c3a06d3`, 6,900 events and 12 state nodes.
- Updated: `7f679c80aa7a474c91b744ce799ee3e7`, 8,602 events and 13 state nodes.
- Both retain `grant`, `download_task`, `announcement` and `session`.
- The only state identity added is `native_state:download_task:cancelled`; none
  of the initial state identities was removed.

These inventory checks select material. They do not complete A26/A34. The final
product batch still needs desktop loading, model identity, actual transfer
animation, language switching and prepared-scene/full-tool boundary checks.
