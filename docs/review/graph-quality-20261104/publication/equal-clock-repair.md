# Equal-clock concurrent execution bands

The released main CI job `126408914275` failed in
`tools/test_data_context.mjs:184`: two independently owned concurrent requests
formed two chains but only one timeline band. The identical tag job passed.
Both requests had actually entered before either could return, so this was a
product defect exposed by a fast fixture, rather than grounds to relax the test.

The JavaScript producer records millisecond timestamps. The old band allocator
treated an end timestamp equal to the next start timestamp as serial execution.
Actual interleaving within the same millisecond was consequently lost.

`trace-executions.js` now retains the original root-entry and final owned-event
IDs and producer-local sequence values. It uses them only for equal-clock lane
ties and only with matching nonempty project, build, run and producer identity,
plus matching optional stream identity. Entry-entry-exit ordering proves overlap;
entry-exit-entry ordering permits band reuse. Duplicate sequence values assigned
to different event IDs invalidate order evidence for that producer scope.

The measured times and zero durations remain unchanged. Separate workers, missing
identity and missing sequence retain the existing time-only presentation. This
change neither assigns cross-producer causality nor manufactures elapsed time.
Boundary witnesses are indexed per band and producer scope; completed clock
ranges are discarded from the tie index.

`tools/test_data_context.mjs` is unchanged, including its two-chain/two-band checks.
Thirty final consecutive native runs pass. The existing
`tools/test_trace_executions.mjs` now has 31 checks, covering interleaved and serial
equal timestamps, reversed completion, clipped recording context, every identity
boundary, missing fields and full/partial duplicate sequence inputs. Loading the
released v0.11.0 allocator in memory reproduces the new deterministic assertion
failure; see `equal-clock-released-failure.json`.

The final trace-execution, lifecycle, recording and exact-API regressions pass.
The 20,000-event equal-clock index check produces 10,000 witnessed serial chains
in one band without changing any input facts; see `equal-clock-20k-index.json`.
Actual Chrome also passes the existing 20,000-event timeline interaction test;
its measurements and screenshot are in `equal-clock-timeline-performance-final/`.
Prettier and ESLint pass for both modified files.

Two initial auxiliary test invocations had setup errors: the browser benchmark
needed the already installed Playwright module path, and the standalone native
data-lifecycle helper required a generated payload argument. They did not expose
additional product failures. The benchmark was rerun with the existing module
and Chrome paths; the generated-payload helper remains part of its parent data
verification workflow rather than an independent argument-free command.
