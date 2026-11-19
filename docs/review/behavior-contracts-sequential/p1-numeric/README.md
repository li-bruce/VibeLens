# Numeric representation regression

Post-slice review found a defect in the definition validator at `22a34384`:
numeric `1` and `1.0` retained their different JSON spellings. An initial equality
could therefore be rejected, and a map could admit duplicate numeric keys.

[Before repair](before.log) was produced from the committed old domain module,
loaded in isolation with the unchanged expression checker. The command returned
1. It did not modify the repository's current implementation or run a mock
replacement for the failing method.

The repair normalizes integral float representations within number domains.
Boolean/integer/string enum identity remains distinct; floating-point enum values
remain unsupported. A second numeric boundary check retains the exact portable
cardinality of Boolean sequences of length at most 52, instead of prematurely
reporting an oversized count.

[Retest commands and results](results.json) preserve logs and checksums. The run
includes 28 domain tests, 38 unchanged scalar tests, 9 baseline/ledger tests,
source syntax/lint/formatting and managed package validation. No native runtime,
new user trial or formal model checker is claimed by these definition checks.

P1 remains in progress. See the [current work ledger](../../../development/behavior-contracts/progress.json).
