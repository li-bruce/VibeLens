"""Presentation hints preserve confirmed meaning and cannot invent flow edges."""

from copy import deepcopy
import unittest
from test_concept_models import draft, approve
from bo_observer import concepts


class ConceptRouteTests(unittest.TestCase):
    def document(self):
        value = approve(draft())
        value["presentation"] = {
            "routes": [
                {
                    "id": "reading",
                    "nodes": ["share", "read"],
                    "edges": ["share-read"],
                    "source_refs": ["U1"],
                },
                {
                    "id": "revocation",
                    "nodes": ["read", "revoke"],
                    "edges": ["read-revoke"],
                    "source_refs": ["U1"],
                },
            ]
        }
        return value

    def test_routes_preserve_confirmed_meaning_and_shared_identity(self):
        value = self.document()
        plain = deepcopy(value)
        del plain["presentation"]
        self.assertEqual(concepts.snapshot(value), concepts.snapshot(plain))
        self.assertTrue(concepts.assess(value)["ready"])
        graph = concepts.assemble(value)
        shared = [node for node in graph["nodes"] if node["id"] == "read"]
        self.assertEqual(len(shared), 1)
        self.assertEqual(shared[0]["layout_routes"], ["reading", "revocation"])

    def test_unknown_and_disconnected_members_fail(self):
        for change in (
            lambda r: r["nodes"].append("revoke"),
            lambda r: r["edges"].append("invented"),
            lambda r: r.update(source_refs=["unknown"]),
            lambda r: r.update(execute="app.py"),
        ):
            value = self.document()
            change(value["presentation"]["routes"][0])
            with self.assertRaises(ValueError):
                concepts.assemble(value)


if __name__ == "__main__":
    unittest.main()
