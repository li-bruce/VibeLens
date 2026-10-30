# Source names and AI names

The toolbar's **AI names** switch controls node, relation, executable-state and transition labels in 2D, 3D and recording replay. It starts on to preserve existing graphs. Its project preference survives view changes, code iterations and reloads.

With the switch off, lexical source symbols, captured field keys, schema keys and state values appear directly. An abstract element without a source symbol uses its declaration ID. Relation labels use their native type or trigger. With the switch on, AI-authored explanations appear; manual node names take precedence. User notes and manual names remain stored in either mode.

## Authoring

Keep explanations in the shared JSON model, separate from source and execution:

```json
{
  "presentation": {
    "names": {
      "nodes": {
        "login": { "en": "Sign in", "zh-CN": "登录" },
        "field:login:out:allowed": { "en": "May sign in", "zh-CN": "允许登录" }
      },
      "edges": { "login_upload": { "en": "Upload after sign-in", "zh-CN": "登录后上传" } },
      "states": { "shared": { "en": "Shared file", "zh-CN": "已共享给接收者" } },
      "events": { "share": { "en": "Share file", "zh-CN": "共享文件" } }
    }
  }
}
```

Keys are exact identities. AI names are an overlay on those IDs; identical explanations on two nodes never merge them. Every relation keeps its original ID and source/target IDs. Source bindings, cross-layer links and replay locations use IDs throughout. Node entries can address generated capture fields or optional source-layer nodes. A plain string uses the conversation's language; localized maps select the current language, then English. Legacy `label`, `machine.labels` and `machine.event_labels` remain compatible fallbacks. If no explanation exists, retain the source name.

Skill graph maintenance writes and reviews these names alongside affected mappings. Prefer a specific action, condition or value in 2–6 words. New labels must contain 1–60 characters on one line. The model contract rejects malformed maps, unsupported locales, empty labels and long labels. Meaning is reviewed against the implementation; a length check cannot establish semantic correctness.

## Boundaries

`graph-names.js` constructs a detached display projection. Renderers, accessible controls, source inspection, search, replay steps and timeline use that projection. Raw source files, node/edge IDs, state values, executable declarations and recording facts remain unchanged. Search accepts both names. A naming change updates labels without resetting layout, camera, selected event, timeline window or transfer evidence. No model call occurs when toggling the switch.

The optional naming overlay in the browser fixture illustrates AI-authored labels over a retained real recording; it does not change that recording or execute business operations.
