# P7 admission repair batch

P7 remains in progress. This batch improves the shared collector before a new
native acceptance run. The two failed Node records in [repair 28](../repair-28/README.md)
remain unchanged; the 421 missing events have not been recovered.

## Changes

- Reuse the canonical model digest only after comparing an exact, type-sensitive
  serialization of the entire loaded declaration. Nested edits, numeric type
  changes and changes between admission boundaries still invalidate the model.
  Actual source and contract bytes are read at every original boundary.
- Validate events with the same bundled Draft 2020-12 schema using the pinned
  `jsonschema-rs` implementation. Python `jsonschema` remains the diagnostic and
  minimal-installation fallback. Portable numbers, payload limits, declared
  fields, identities, provenance and atomic publication keep their existing checks.
- Keep the dependency in the external observer environment. No new package or
  state authority is added to business applications. See
  [upstream Python documentation](https://github.com/Stranger6667/jsonschema/tree/python-v0.60.1/crates/jsonschema-py)
  and [dependency notices](../../../../../THIRD_PARTY_NOTICES.md).
- Clarify the Skill's repair order: collect findings, fix the common batch, run
  targeted regressions, then complete acceptance in the existing trial. New
  conversations are reserved for an explicit acceptance requirement.

## Validation boundaries

The new model tests exercise nested mutation and restoration, Python-equal values
with distinct JSON types, dictionary order, shared children and invalid values.
An additional atomic-admission case changes a nested capture declaration between
the two checks and requires the entire group to be rejected without publication.

The accelerated schema tests compare every top-level property's type mutations,
required-field omissions and nested invalid facts against the original validator.
They also check identical diagnostic text, missing optional acceleration, safe
integer limits, nonfinite numbers and payload limits. Other protocol and native
business checks remain in the complete repository gate.

## Measurements

All measurements use detached source copies and the original bounded transport.
They do not run business operations or edit application records. Measurement
outputs distinguish three different workloads:

1. Serial replay of 2,032 original native envelopes, with profiler overhead.
2. A synthetic 10,160-envelope burst with 475 snapshot barriers in 3.7 seconds.
   Both old and updated implementations still overflow the 8,192-item waiting
   queue. These failures are retained; they establish no lossless-throughput claim.
3. Derived transport replay of the known envelopes in the two failed ordinary
   records: a 2,441-envelope warm prefix, followed by 9,029 retained events and
   32 original native snapshots over 3.7 seconds. Only collector metadata is
   removed and original producer sequence numbers restored. This input is
   incomplete because the original producer discarded 421 events.

With active recording and full-view HTTP polling, the third workload introduces
no additional drop or transport error for either implementation. Its measured
queue peak changes from 7,166 to 6,199; burst-plus-drain time changes from 22.41 s
to 14.83 s. These are individual local observations, with an evenly paced replay,
not a recreation of original scheduling or proof of native acceptance. Native
recording must still pass on the complete original workload and declared fields.

The following limits remain fixed: native waiting queue 8,192, browser queue
4,096, batch 64 events / 256 KiB, envelope 24 KiB, request deadline 1,000 ms and
two attempts. Snapshots remain ordered separate requests. No preferred business
schedule, field removal, queue enlargement or raw-record repair is used.

## Failures retained

- The first model-cache regression assumed the minimal fixture had a `labels`
  member. It failed with `KeyError`; the corrected case mutates an existing nested
  capture type and verifies whole-batch rejection and subsequent restoration.
- Four unchanged Windows junction tests failed inside the sandbox. Their same
  host commands pass without changing assertions or containment behavior.
- The high-snapshot synthetic burst still overflows, and a discarded snapshot
  witness can cause a subsequent transport rejection. This remains distinct from
  the application-shaped partial replay and from a complete native run.
- A sandbox dependency download could not replace its temporary metadata file;
  the identical pinned host install succeeded. No global proxy or installed
  provider was changed.

## Final native acceptance

The 92 targeted tests and the complete repository gate, including database
checks, pass. Both shipped examples passed standard maintenance and their
accepted receipts were frozen. [Python drive](../python-current-repair29/README.md)
and [Node observe](../node-current-repair29/README.md) then passed complete native,
recording, independent desktop and canonical acceptance on provider `0ac64bc0`.
Node retained all 666 fields and original limits; its two records contain
2,514 and 9,882 events without gaps. The stronger synthetic overflow above
remains a capacity boundary, separate from the accepted real workload.
No main merge, release or site deployment is included.
