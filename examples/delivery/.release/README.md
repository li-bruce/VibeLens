# Reviewed starting point

The current snapshot is `source-flow-20261026`. It binds the published delivery example
to its reviewed source, graph, copied runtime and verification results.

`tools/demo.py` restores this snapshot only for a fresh checkout, then checks the
current source. It does not approve local edits. `tools/verify.py` reruns the tests
against the same reviewed candidate. Earlier reviewed stages remain available.

The latest maintenance record updates witnessed workflow transfers and business-level replay in the shared viewer. Business source, state definitions, capture requirements and independent expectations are unchanged. The copied assets and runtime inventory were explicitly reviewed and sealed, then mapping, state rules, business and project checks passed again. Previous acceptance records remain intact.

The following notes describe the earlier database-view update.

This update installs the shared database observer and typed data views. The
delivery application keeps its existing state declaration, behavior and capture
requirements. Its layout regression fixture includes the new data roles. The
example does not configure a database catalog; separate real-database fixtures
exercise those adapters.

Mapping, state rules, business expectations and project checks passed. See the
[failure, repair and retest evidence](../../../docs/review/db-vis/delivery-acceptance.md).
This receipt records source consistency and executed checks; it is not a digital
signature or a proof of every possible behavior.
