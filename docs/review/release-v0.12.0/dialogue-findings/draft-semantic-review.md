# Revised draft: semantic review

Status: both corrections verified in the saved draft; implementation not yet tested.

A read-only review of round 03 compared the generated draft with the simulated
user's answers. Most requirements were represented: distinct session/grant
identities, one bound file-review machine, self-review rejection, new uploads
after rejection, one recipient, uploader-only sharing/revocation, and download
behavior at the revocation boundary.

Two details still needed correction before confirmation:

1. Sharing declared state applicability as `none`, although it reads file-review
   approval. The existing protocol can express `models: [file_review]` and
   `mode: read`; grant/message mutations remain separate native effects.
2. The shared reviewer predicate's fact timing said only “before review approval”
   although the same condition governs approval and rejection.

The coordinating AI sent a natural-language correction in the separate chat.
This was a semantic comparison with the stated intent, not a structural validator
failure. It demonstrates why a structurally valid draft still needs explicit
meaning confirmation. The original draft remains in the trial's review files;
later correction and implementation results must be recorded separately.

The saved revision 02 now declares sharing as a read of `file_review`; the
canonical graph builder generates `operation-state:share:file_review` with
`reads_state`. The reviewer fact timing covers approval or rejection in the
current request. The original two mistakes remain in
`review/round-03/discovery.presented.json`; corrected snapshots and a semantic
diff are in `review/round-03/revision-02/`. This retest verifies draft meaning and
projection only, not the future application's behavior.
