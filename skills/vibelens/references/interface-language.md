# Interface language

VibeLens starts in English. During discovery and subsequent conversation, the coding
assistant records the user's language:

```bash
python SKILL/scripts/bo_design.py language --root PROJECT --locale zh-CN --source "Current Chinese conversation"
```

Use `en` for English and unsupported conversation languages. Run this before giving
the user the graph URL; update it when the user changes language. This command works
before a business graph exists. It writes only `bo_stategraph/config/interface.json`.

The viewer resolves language in this order: explicit `?lang=`, saved personal choice,
conversation language, English. A manual switch persists in the project's personal
view settings. A browser's system language alone does not select Chinese.

Language selects interface text and the generated semantic-name overlay. Source
symbols, IDs, raw fields, original declarations and personal notes stay unchanged.
Existing personal layouts survive a switch.
`/api/design` includes `locale` even when no discussion focus is available. When the
conversation language changes, the live viewer reloads after saving its layout unless
the user has chosen a language explicitly.

An expired, absent or unavailable discussion focus clears its highlights silently.
Valid confirmed focus highlights the graph directly, without a discussion bar.
Click empty canvas or press Escape to dismiss it. Dismissal survives reloads; a newly
confirmed scope can focus again. User answers and revisions stay in the coding conversation.

## Generate names with the graph

Before sharing a graph URL and after each affected coding batch:

1. Run `bo_names.py inventory --root PROJECT --out review/name-inventory.json`.
   The inventory describes current business/state/rule concepts, source entries,
   parameters, storage and authored relation details. Each item includes its ID,
   layer and a fingerprint of its current meaning/source context.
2. Write `bo-semantic-names/v1` JSON with `locales: ["en", "zh-CN"]`, `names`
   and `basis`. Both maps use inventory categories and exact IDs. Copy each item's
   fingerprint into `basis[category][id]`; write its concise language map into
   `names[category][id]`. This is the coding assistant's translation work.
3. Run `bo_names.py apply --root PROJECT --input review/semantic-names.json`, then
   `bo_names.py check --root PROJECT`. The managed artifact lives at
   `bo_stategraph/config/semantic-names.json`. The viewer reloads it with the graph.

Translate the layer's meaning: a business action says what the user does, a state
names an object's condition, a rule names the decision/fact, an API names an entry,
and code describes the actual function or parameter. Do not reuse one variable's
wording for every conceptual occurrence. Keep filenames and source identifiers in
details and source-name mode. Relations describe the specific dependency or branch;
mechanical relation types use the viewer's localized legend.

`bo_sync scan` lists missing/stale translations after the artifact is enabled.
`change_sync verify` reports them under project checks. Review the affected meaning
before renewing its fingerprint. A new translation cannot authorize behavior drift.
Legacy projects without the artifact remain readable; migrating them requires this
generation step, not merely changing the language selector. Runtime rendering never
guesses a translation or sends source to an external model.
