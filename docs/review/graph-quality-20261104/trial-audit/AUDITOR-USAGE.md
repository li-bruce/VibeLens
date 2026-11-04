# Existing-evidence trial auditor

Run only after the trial conversation has finished its native and browser checks:

```powershell
.venv/Scripts/python.exe docs/review/graph-quality-20261104/trial-audit/audit_accepted_trial.py --phase remark-v2 --out remark-v2-independent-01
```

The default trial is `VibeLensTrials/graph-quality-dialogue-20261104-01` beside the
repository. `--trial PATH` selects a different root. Outputs remain in this audit
directory. Existing JSON or Markdown output names are refused.

Default receipts come from `review/PHASE/`. Select a differently named artifact
with `--receipt docs=review/remark-v2/source-docs.json`; supported kinds are
`current`, `docs`, `api`, `browser`, `replay` and `runtime`.
`--recording PATH` selects the saved browser recording. If replay used another
recording, provide its existing JSON with `--replay-recording PATH`.

The script imports only the Python standard library. It reads declarations,
accepted/check receipts and declared source hashes. It does not import the app,
run project commands, make requests, read environment/cookie/secret/database
content or write inside the trial. It writes a new JSON and Markdown report here.

Missing, stale, changed-during-audit or identity-unbound evidence remains pending.
Mapping, state rules, project checks and business assertions are reported
separately. Human review still covers graph/timeline appearance, projected state
intervals, intended remark privacy, changed layout positions and receipts that
cannot identify their build. Candidate IDs are linked through native receipts;
this script does not rebuild the protected native candidate independently.

The auditor was initially prepared without running against the active iteration.
Later runs are retained separately as `remark-v2-independent-01` and `-02`;
the second run's selected receipts and remaining revision flags are explained
in `remark-v2-independent-02-notes.md`. Its existence alone implies no trial pass.
