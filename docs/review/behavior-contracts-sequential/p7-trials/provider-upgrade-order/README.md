# Begin the change before adopting a new provider

The Node trial selected the new provider before starting its next coding change.
Its application inputs were unchanged, but both `check` and `begin` rejected the
new candidate: the accepted receipt includes executed observer-tool fingerprints.
The original failed commands and their outputs are retained here.

The old and new read-only snapshots differed only in the candidate ID and the
hashes of `bo_observer/service.py` and `bo_observer/web/bo_design.py`. The preserved
old provider still produced the exact accepted candidate
`a8f0eec865999f12ec6885078de42cab1a548a0d2a6d7976fc442fda0ead7e86`.
Application source, semantic declarations, validation contracts and managed SDK
bytes were equal. The two providers' public entry and `begin` implementation
were also byte-identical.

After checking those prerequisites again, the old provider ran the normal `begin`
command once, preserving the real accepted starting point. The new provider then
ran recall and managed integration checks successfully. All subsequent coding,
inspection and verification use the new provider. No active pointer, baseline,
manifest or accepted ID was manually rewritten; no guard was removed.

[Results and original-file hashes](results.json) establish this handoff only.
They do not establish that the later business change has passed acceptance.

The maintained [continuous-development guide](../../../../../skills/vibelens/references/continuous-development.md)
now states the normal order and this narrowly checked recovery case. If the old
installation no longer reproduces the accepted inputs, this recovery does not
apply. Runtime code is unchanged; strict rejection remains the expected behavior
for an altered or unverified starting point.
