# Source explanations for mapped code

Use this reference when creating or changing API handlers, mapped functions, or important parameters. The coding agent maintains source documentation with the implementation; the user confirms business meaning in the existing dialogue.

## Write explanations with the implementation

Give each authored, mapped function a concise source summary of its actual action, condition, or effect. Document important inputs, returned values, and relevant side effects or exceptions. Explain units, identity, optional values, and state meaning when the name and type leave them unclear.

- Python: use a function docstring, with `Args`/`Parameters` and relevant `Returns`/`Raises` sections.
- JavaScript/TypeScript, including React/Vue source: use adjacent JSDoc and `@param`/`@returns` descriptions. Type annotations remain authoritative for types.
- API handlers: describe the resource/action and actual behavior. The route registration supplies HTTP method and path. A catch-all dispatcher describes dispatch; a request collection wrapper does not define a concrete endpoint.
- Important parameter nodes: bind the exact declaration and parameter name, then extract that parameter's description. A collected event output remains an observation field; its explanation must not claim it is a physical function argument.

```python
def download_file(file_id: str, actor_id: str) -> bytes:
    """Return the file bytes after checking the actor's current access.

    Args:
        file_id: Identity of the stored file to read.
        actor_id: Authenticated actor checked for this request.

    Returns:
        The original stored bytes.

    Raises:
        PermissionError: The actor cannot currently download the file.
    """
```

This illustrates documentation, not a permission rule to add to unrelated software. Describe the actual implementation and confirmed requirements.

## Extract and display

The scanner extracts documentation with its declaration path, symbol and line range. Verified source bindings and file fingerprints identify the implementation. Comments explain source; they do not establish business confirmation, execution, or data transfer.

Keep concrete API registrations separate from shared handlers, source symbols and technical capture anchors. Several routes can share one handler; one route can call several functions or run repeatedly. Preserve those identities and connect their representations. Deduplicate only the same registration under the existing identity criteria.

Register HTTP observation against the actual handler source, method and literal route. A source mapping alone cannot establish which route ran. Exact observation-source metadata connects recorded request boundaries to their API representation; ordinary source links remain static. Verify Graph and Timeline against different routes sharing a handler, both methods of a combined registration, and a denied/error response. The API interval must retain the original request's start, end, values and identity. Recordings freeze this minimal API structure independently of the optional full code view.

Use the first useful sentence as a short explanation and retain complete comments for inspection. Localized aliases follow the conversation language while exact source text, identifiers and IDs remain available. Renaming explanations changes no route registrations, state values, bindings or recording references. Layout similarity uses physical source metadata and identifiers, not translated aliases.

Missing documentation remains missing. Do not derive source comments from AI display labels, copy one function summary to unrelated parameters, or remove undocumented functions from coverage. For adopted code, report gaps and add accurate comments to authored mappings through a managed batch. Third-party source can retain an explicit explanation gap while remaining represented.

## Check affected coding batches

After scan and inspection, run:

```text
python SKILL/scripts/bo_code.py docs --root PROJECT --strict
python SKILL/scripts/bo_code.py api-check --root PROJECT --strict
```

New projects include this check in their verification entrypoint for authored mapped functions, API handlers and explicitly represented important parameters. Existing projects keep all prior gates and report missing explanations until authored mappings are documented; preserve baselines and coverage.

For HTTP applications, the strict API check also detects a newly added route without a qualified observation registration. Keep explicit partial/adoption coverage in its report; a configured wrong or ambiguous selector fails the normal mapping gate even when the full code view is disabled. Coverage and correctness of selected mappings are separate results.

When a signature, route, parameter meaning or behavior changes, update its comment and regenerate source metadata. Verify in an isolated case that missing mapped documentation is detected and edited source invalidates stale documentation evidence. Source/explained-name switching must retain exact node/edge IDs. Report source-explanation completeness separately from business correctness and observation completeness.
