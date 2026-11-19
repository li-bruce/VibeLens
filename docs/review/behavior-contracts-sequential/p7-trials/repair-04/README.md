# Managed native dependency upgrade

The isolated Node observe trial stopped at a real upgrade failure: its existing
two-module receipt could not accept the third module introduced by repair 03.
`native-upgrade-first.log` reproduces the failure with that installed package;
`native-prior-integration.json` preserves the actual old inventory. No application
source or receipt was changed for this diagnostic.

The maintained installer now recognizes the exact released JavaScript inventory
and adds `bo_http.mjs`. The earlier Python model-registry addition uses the same
migration checks. Source maps and wire protocols must match, and unknown members
or edited dependencies are still refused. The original receipt is archived by
its SHA-256 before replacing files. Application definitions, business code and
personal layout are outside the write set.

`migration-first.log` retains the failing regression before the fix.
`integration-final.log` checks successful migration, unchanged personal settings,
idempotence, unsupported inventories/protocols, local edits, archive conflicts,
copy failures and receipt-write failures. Failed writes restore old dependency
bytes; inspection remains strict and never repairs an old receipt automatically.

An audit of release `03c3488a` found the older protocol map without
`snapshot_registry`. `pre-registry-first.log` retains the initially rejected
Python and JavaScript cases. `integration-final-v2.log` checks the exact released
upgrade as well: that missing field is supported only with the known old inventory;
arbitrary protocol substitutions still fail. The original intermediate logs and
installations are retained separately from the final candidate.

`prior-candidate/` retains the first managed-example run. Its team-archive check
rejected `candidate changed while checks were running` when the pre-registry
compatibility correction changed canonical bytes. This is a valid gate rejection,
not a business failure. Both examples are regenerated and rechecked against the
fixed candidate; the earlier pass is not reused for the new source.

The actual Node trial applied the independent package through the managed entry;
`native-upgraded-integration.json` preserves its new inventory. An independent
rerun of the unchanged diagnostic from repair 03 now captures one matching API
return for each actual 403, 400 and 401 response. Source fingerprints are identical
before and after that diagnostic (`native-origin-result.json` and
`native-origin-events.json`). This is in-progress application evidence; full
trial, iteration and browser acceptance still remain open.

Final framework gates pass: 18 integration regressions; the full runner reports
1,105 test records across 95 unittest suites, with one host file-symlink skip;
238 Python and 142 JavaScript modules pass source checks. Both maintained
examples pass verification, acceptance and current-source checks. Their frozen
round `behavior-contracts-p7-repair04-20261120` also passes the clean Git export
check without regeneration or reapproval. Commands, outputs and candidate hashes
are indexed in `results.json`.
