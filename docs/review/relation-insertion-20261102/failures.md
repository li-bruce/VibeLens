# Failure and repair record

## 01 — nested registered composition

The first unit run executed 20 tests; 19 passed and the nested-composition case failed (`KeyError: leaf_path`). A summary already represented by its own proof had disappeared from the path-query inventory. A higher-level registered composition could therefore no longer use that declared meaning, even though its raw registration and complete evidence path existed.

Repair: keep admitted display edges and registered proof claims as separate inventories. Typed queries may use a previously represented claim; every successful result must expand to retained leaf edge IDs with continuous endpoints. Duplicate aliases do not become extra path facts. Search/expansion budgets retain the original summary on exhaustion.

The regression checks both the nested proof and that all expanded leaf IDs remain admitted edges.

## 02 — non-JSON Python payload error normalization

The expanded 24-test run found that an invalid Python set payload reached the shared schema serializer before the relation contract could reject it. The mutation was rejected, but raised `TypeError` instead of the module's `ValueError` contract. Validate portable value types first; also reject object cycles, excessive nesting and unsafe integers before schema validation. The original shared protocol and its validation rules remain unchanged.

## 03 — runtime integration test used the wrong history API

The added actual-probe case reached the collector, then failed because the test treated `EventHistory` as a Python list. Use its public `snapshot()` API for assertions. The collector and its retention implementation remain unchanged. [Original output](failure-03-probe-test.stderr.log) is preserved separately from the successful retest.
