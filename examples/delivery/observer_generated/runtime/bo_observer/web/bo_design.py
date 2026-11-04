"""Read-only design graph and conversation focus, before or during coding.

The user answers in their coding assistant. This module only projects authored
requirements and stores which nodes that conversation is currently discussing.
"""

import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit
from .interface_language import read_language, set_language

try:
    from ...behavior_model import contained
    from ...requirements_dialogue import assess, read
    from ...sync_io import write
    from ...view_preferences import file_lock
except ImportError:
    from behavior_model import contained
    from requirements_dialogue import assess, read
    from sync_io import write
    from view_preferences import file_lock


def bo_digest(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()
    ).hexdigest()


class BODesign:
    def __init__(self, root, discovery=None):
        self.root = Path(root).absolute().resolve()
        config = self.root / "sync.json"
        cfg = read(config) if config.exists() else {}
        self.path = contained(self.root, discovery or cfg.get("discovery", "discovery.json"))

    def document(self):
        doc = read(self.path)
        result = assess(doc)
        if not result["valid"]:
            raise ValueError(
                "Invalid discovery record: " + json.dumps(result["errors"], ensure_ascii=False)
            )
        return doc

    def _identities(self, doc):
        nodes = [n for net in doc["networks"] for n in net["nodes"]]
        for n in nodes:
            links = n.get("model_nodes", [])
            if not isinstance(links, list) or any(
                not isinstance(x, str) or not x.strip() for x in links
            ):
                raise ValueError("Invalid design node ID: " + n["id"])
        return {n["id"]: (n.get("model_nodes") or [n["id"]]) for n in nodes}

    def snapshot(self):
        language = read_language(self.root)["conversation_locale"]
        if not self.path.exists():
            return {"available": False, "locale": language}
        doc = self.document()
        path = contained(self.root, "bo_stategraph/config/design-focus.json")
        focus = read(path) if path.exists() else {"schema": 1, "nodes": [], "label": ""}
        if (
            not isinstance(focus, dict)
            or focus.get("schema") != 1
            or not isinstance(focus.get("nodes"), list)
            or any(not isinstance(x, str) for x in focus["nodes"])
            or not isinstance(focus.get("label"), str)
        ):
            raise ValueError("Invalid conversation focus configuration")
        return {
            "available": True,
            "locale": language,
            "revision": bo_digest(focus),
            "nodes": focus["nodes"],
            "label": focus["label"],
            "stale": bool(
                focus.get("discovery_revision") and focus["discovery_revision"] != bo_digest(doc)
            ),
        }

    def focus(self, nodes, label="", decision=None):
        """Resolve discussion IDs through the complete design graph, including edges."""
        doc = self.document()
        identities = self._identities(doc)
        graph = self.view()["model"]
        graph_nodes = {item["id"] for item in graph["nodes"]}
        graph_edges = {item["id"]: item for item in graph["edges"]}
        if decision:
            item = next((d for d in doc["decisions"] if d["id"] == decision), None)
            if item is None:
                raise ValueError("Discovery question not found")
            nodes = item["affects"]
        resolved = set()
        for reference in nodes:
            if doc.get("schema") == "business-discovery/v2":
                from ..concepts import resolve

                references = [resolve(doc, reference)]
            else:
                references = identities.get(reference, [reference])
            for reference in references:
                if reference in graph_edges:
                    edge = graph_edges[reference]
                    resolved.update((edge["from"], edge["to"]))
                else:
                    resolved.add(reference)
        ids = sorted(resolved)
        known = graph_nodes | {mid for values in identities.values() for mid in values}
        cfg = read(self.root / "sync.json") if (self.root / "sync.json").exists() else {}
        if cfg.get("model"):
            from ..model_io import read_model

            known.update(n["id"] for n in read_model(contained(self.root, cfg["model"]))["nodes"])
        if set(ids) - known:
            raise ValueError("Focus nodes not found: " + ", ".join(sorted(set(ids) - known)))
        if len(ids) > 50 or not isinstance(label, str) or len(label) > 120:
            raise ValueError(
                "A focus graph allows at most 50 nodes and a 120-character description"
            )
        path = contained(self.root, "bo_stategraph/config/design-focus.json")
        with file_lock(path.with_suffix(".lock")):
            write(
                path,
                {
                    "schema": 1,
                    "nodes": ids,
                    "label": label.strip(),
                    "discovery_revision": bo_digest(doc),
                },
            )
        return self.snapshot()

    def view(self):
        """A declaration-only projection using reserved implementation node IDs."""
        doc = self.document()
        project = (
            (
                read(self.root / "intent.json").get("project_id")
                if (self.root / "intent.json").exists()
                else None
            )
            or doc.get("project_id")
            or self.root.name
        )
        if doc.get("schema") == "business-discovery/v2":
            from ..concepts import assemble

            model = assemble(doc)
            model["project_id"] = project
        else:
            from .design_legacy import legacy_model

            identities = {key: values[0] for key, values in self._identities(doc).items()}
            model = legacy_model(doc, identities, project)
        return {
            "stage": "design",
            "layout_id": doc.get("layout_id", project),
            "model": model,
            "manifest": {"build_id": bo_digest(doc), "bindings": {}},
            "binding_status": {"status": "design"},
            "events": [],
            "machine": {"configurations": [], "current": None, "journal": []},
            "authority": {"basis": {}, "parameters": {}},
            "health": {"errors": 0, "dropped": 0},
            "busy": False,
            "historical": False,
            "available_cases": ["live"],
        }

    def preview(self, url, nodes=(), *, max_nodes=12, view="business", locale=None):
        """Derive a bounded conversation diagram from the same Web design data."""
        from ..graph.focus_graph import extract
        from .design_preview import markdown

        parsed = urlsplit(url)
        if (
            parsed.scheme not in ("http", "https")
            or not parsed.hostname
            or parsed.username
            or parsed.password
        ):
            raise ValueError("preview requires an HTTP graph URL without credentials")
        if any(c in url for c in '\r\n<>"()\\'):
            raise ValueError("unsafe graph URL")
        envelope = self.view()
        document = self.document()
        model = {**envelope["model"], "revision": envelope["manifest"]["build_id"]}
        if view not in {"business", "state", "rules", "all"}:
            raise ValueError("Unknown conceptual view")
        if nodes and document.get("schema") == "business-discovery/v2":
            from ..concepts import resolve

            edges = {edge["id"]: edge for edge in model["edges"]}
            resolved = []
            for reference in nodes:
                ident = resolve(document, reference)
                # A question may concern a transition or a cross-model edge.
                # Preserve both endpoints instead of treating the edge as a node.
                edge = edges.get(ident)
                resolved.extend((edge["from"], edge["to"]) if edge else [ident])
            nodes = list(dict.fromkeys(resolved))
        candidate_nodes = [
            item
            for item in model["nodes"]
            if view == "all"
            or item.get("layer") == view
            or (view == "rules" and item.get("policy_role"))
        ]
        # Put decisions and transitions before their lower-level input detail in
        # a bounded conversation preview. Otherwise a rule view can omit the very
        # operation result that the user is being asked to confirm.
        priority = {
            "rule_operation": 0,
            "transition": 0,
            "state": 1,
            "state_model": 1,
            "rule_expression": 1,
            "event": 2,
            "guard": 2,
            "fact": 3,
            "rule_predicate": 4,
        }
        if view in {"state", "rules"}:
            candidate_nodes.sort(key=lambda item: priority.get(item.get("concept_kind"), 5))
        candidates = [item["id"] for item in candidate_nodes]
        # The original format mixes conditions and states into its business
        # network. Preserve that complete overview until the project migrates.
        if view == "business" and document.get("schema") == "business-discovery/v1":
            candidates = model["graph_roots"]
        anchors = list(nodes) or candidates[:max_nodes]
        if not anchors:
            raise ValueError("No declared nodes in the requested conceptual view: " + view)
        focused = extract(model, anchors, depth=0 if not nodes else 1, max_nodes=max_nodes)
        # Display language and reused boundary glyphs do not alter the focus
        # identity, its dependency records, or the user's confirmed meaning.
        locale = locale or read_language(self.root)["conversation_locale"]
        text = markdown(focused, document, url, view, locale)
        return {
            "markdown": text,
            "focus": focused,
            "url": url,
            "discovery_revision": model["revision"],
            "view": view,
            "locale": locale,
        }

    def export_preview(self, result, name):
        """Preflight both preview artifacts before writing either of them.

        A Markdown preview has a companion JSON artifact. Checking only the
        requested Markdown path could overwrite discovery.json through that
        companion, destroying the very declaration being reviewed.
        """
        target = contained(self.root, name)
        companion = target.with_suffix(".json")
        from ..workflow.artifact_paths import guard_outputs

        guard_outputs(
            self.root,
            [target.relative_to(self.root), companion.relative_to(self.root)],
            inputs=[self.path],
            suffixes=(".md", ".markdown", ".json"),
        )
        if target.suffix.lower() not in {".md", ".markdown"}:
            raise ValueError("Preview output must use a Markdown extension")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result["markdown"], encoding="utf-8")
        write(companion, result)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=["show", "focus", "preview", "language"])
    p.add_argument("--root", default=".")
    p.add_argument("--discovery")
    p.add_argument("--nodes", nargs="*", default=[])
    p.add_argument("--decision")
    p.add_argument("--label", default="")
    p.add_argument("--locale", choices=["en", "zh-CN"])
    p.add_argument("--source", help="Conversation message or explicit language preference")
    p.add_argument("--url", help="Actual graph URL, checked by the calling developer")
    p.add_argument("--max-nodes", type=int, default=12)
    p.add_argument("--view", choices=["business", "state", "rules", "all"], default="business")
    p.add_argument(
        "--out", help="Project-relative Markdown output; also writes matching focus JSON"
    )
    a = p.parse_args()
    try:
        design = BODesign(a.root, a.discovery)
        if a.action == "language":
            print(json.dumps(set_language(design.root, a.locale, a.source), indent=2))
            return 0
        if a.action == "preview":
            result = design.preview(
                a.url or "", a.nodes, max_nodes=a.max_nodes, view=a.view, locale=a.locale
            )
            if a.out:
                design.export_preview(result, a.out)
            print(result["markdown"])
            return 0
        result = (
            design.focus(a.nodes, a.label, a.decision) if a.action == "focus" else design.snapshot()
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
