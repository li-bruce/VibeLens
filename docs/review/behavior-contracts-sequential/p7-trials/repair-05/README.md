# Application source view after a managed upgrade

An independent inspection of the in-progress Node trial found a managed upgrade
receipt, its archived predecessor and a registered behavior definition in the
application's engineering tree. The source scanner correctly kept application
code, but display ownership did not cover these newer observer artifacts.

The shared source policy now prunes `bo_stategraph/migrations` before directory
descent, alongside preferences and recordings. A narrow first-party source root
still restores application code inside a reserved directory. Hash-only watches
still detect changes. Physical source/API bindings into excluded storage fail.

Both the complete code view and the independent file view use the exact
definition paths from the validated project envelope. The managed integration
receipt is display-only metadata. No ownership is inferred from an ordinary
filename, from a watched-file entry or from an implementation's `support` label.
Project-owned adapters and native state executors remain inspectable.

## Failure, repair and retest

- `scope-first.log`: migration backups were traversed and accepted as physical
  source. The run also encountered the existing Windows junction test's sandbox
  restriction; its unchanged test subsequently ran with host filesystem support.
- `display-first.log`: the first test fixture used an invalid empty integration
  receipt. The existing strict installer rejected it. The fixture was corrected
  to use a real managed installation; validation was not relaxed.
- `display-reproduction.log`: the registered definition and receipt still appeared
  in the tree, before the display fix.
- `focused.log`: 75 tests pass, with one existing Windows file-symlink permission
  skip. Checks cover source ownership, both projections, reference relocation,
  narrow overrides, native executors, watched hashes and ordinary application
  files with observer-like names.
- `native-structure-before.json` and `native-structure-after.json`: read-only
  inspection of the actual Node trial with the preceding installed provider and
  the repaired canonical provider. Five definition/receipt/archive entries leave
  the engineering projection; the source inventory is identical. No application
  source, model or recording is edited by this inspection.

The temporary trial viewer was offline during an initial HTTP inspection, so
the source comparison uses each provider's read-only project projection directly.
It is not a browser screenshot or complete native acceptance result.

The repaired candidate's source, managed-example, full-regression and clean-export
receipts are indexed in `results.json`. P7 remains open for both native trials,
business iterations, source-only refactors and final desktop/product evidence.

Final framework checks pass: 1,107 reported test records across 95 suites, with
one Windows file-symlink skip; 238 Python and 142 JavaScript modules pass source
checks. Both example approvals and their clean Git export pass without changing
application source. The independent native trials remain in progress.
