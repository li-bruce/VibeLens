# Demo startup repair

The first public v0.11.3 check exposed an iframe startup race. Both localized demo pages rendered their graphs but raised `Failed to fetch`: the initial English iframe document was replaced while its real case-data response was loading. The [first public result](../public-v0.11.3-01/chrome-pages.json) and [exact stack and aborted request](../public-v0.11.3-01/demo-diagnostic.json) remain unchanged.

The iframe now starts at `about:blank`; the existing story stage chooses its first version and language. Same-version scene changes reuse that document. Ready messages and actual fetch errors retain their original behavior. The published v0.11.3 tag, Skill archive, engine and maintained examples stay unchanged.

Both [first local Chrome run](local-chrome/result.json) and [final bounded regression](local-chrome-final/result.json) passed six fresh contexts: English and Chinese three times each. Each test holds the real child case-data response until the parent selects its scene, verifies one localized document navigation, then follows the native foundation-to-run transition and checks rendered nodes, relations and the recorded event. Every context had zero page errors and zero failed requests.

[Summary and source hashes](summary.json) record the unchanged Skill tree, syntax, source-artifact and full formatting checks. The existing `timeline-browser` CI job now includes the regression alongside all previous checks. Deployment and final public Chrome rechecks remain separate evidence.
