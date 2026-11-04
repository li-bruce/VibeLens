# Reserved subtree scope inconsistency

The isolated fixture confirms a functional inconsistency. Both
`bo_stategraph/config/local_api.py` and `bo_stategraph/data/local_api.py` are
accepted as source and physical bindings by the default shared scope. Direct
AST/API extraction identifies their real literal Flask registrations.
`code_graph/filesystem.py` unconditionally removes both parent subtrees.
Adding explicit first-party roots for them does not restore filesystem entries.

This is more than a hidden configuration file. Full/API and project-only
CodeGraph views both raise `KeyError('bo_stategraph/config/local_api.py')` because
`code_graph/index.py:181` expects a file owner for every indexed symbol. Mandatory
API snapshots also use that builder, so this can affect the graph without the
optional code view being open. Normal observer preferences alone do not create
this crash; it requires eligible executable source in one of the hidden paths.

[result-01.json](result-01.json) retains both actual view exceptions. Its final
prose incorrectly described the project-only view as merely omitted; the stored
exception was already correct. [result-02.json](result-02.json) explicitly
corrects that sentence and measures direct filesystem omission separately.

The intent to keep personal preferences and recordings from changing the source
graph is reasonable. Documentation alone cannot resolve the contradictory
eligibility and failed explicit override. A future fix should either classify
these reserved outputs through the shared policy, honoring explicit first-party
overrides, or narrow filesystem-only suppression to the exact observer-owned
artifacts while retaining eligible source owners. Existing preference/recording
invalidation protections and full-project discovery must remain intact.

No product changes were made. Tests used only two temporary source files and
canonical static functions; no application imports, requests, active-trial
writes, database reads or native acceptance commands were involved.
