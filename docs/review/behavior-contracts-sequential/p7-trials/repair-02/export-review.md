# Clean export checks

The final `clean-export.json` passes both native example checks from the staged
Git export and their frozen approvals, without regenerating or reapproving them.
The canonical provider is separately exported from the same staged tree at
`.validation/p7-repair02-provider/skills/vibelens`. Its locked viewer dependencies
were hydrated and hash-checked before this final check.

Earlier attempts are retained:

- The sandbox's default dependency cache refused an atomic replacement. The
  retry uses a project-local cache.
- `clean-export-canonical-drift.json` rejected a newer Node adapter being worked
  on for the next repair while checking the earlier staged candidate. The strict
  source comparison correctly failed; the frozen provider removes that mismatch.
- `clean-export-unhydrated-provider.json` rejected missing viewer dependency
  bytes in that fresh provider. Hydration supplies the locked artifacts.

These were export/setup failures, not new business-test approvals. The final
receipt identifies the exact tested tree. Later evidence-only additions do not
change either native example or the frozen provider's source.
