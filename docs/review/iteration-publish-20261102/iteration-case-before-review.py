"""Later-turn clarification uses existing identities, history and actual previews."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/vibelens/scripts"
sys.path.insert(0, str(SCRIPTS))

from bo_observer.workflow.requirements_dialogue import assess
from bo_observer.workflow.sync_io import write
from bo_observer.web.bo_design import BODesign


def confirmed():
    """The existing project has confirmed sharing and an unrelated message branch."""
    return {
        "schema": "business-discovery/v1",
        "project_id": "sharing",
        "goal": "Upload and share files with selected recipients",
        "sources": [
            {
                "id": "U0",
                "kind": "user",
                "text": "Recipients can download a shared file. Send them a message when I share it.",
                "locator": "Synthetic initial confirmation",
            }
        ],
        "networks": [
            {
                "id": "sharing",
                "title": "Share a file",
                "actors": ["Owner", "Recipient"],
                "trigger": "Owner shares an uploaded file",
                "outcome": "Recipient can download it",
                "nodes": [
                    {
                        "id": ident,
                        "kind": "condition" if ident == "allowed" else "action",
                        "label": label,
                        "source_refs": ["U0"],
                        "model_nodes": ["business." + ident],
                    }
                    for ident, label in [
                        ("upload", "Upload file"),
                        ("share", "Share file"),
                        ("allowed", "Recipient may download"),
                        ("download", "Download file"),
                        ("message", "Receive sharing message"),
                    ]
                ],
                "edges": [
                    {
                        "id": ident,
                        "from": start,
                        "to": end,
                        "relation": relation,
                        "label": label,
                        "source_refs": ["U0"],
                    }
                    for ident, start, end, relation, label in [
                        ("uploaded", "upload", "share", "flow", "Select uploaded file"),
                        ("shared", "share", "allowed", "flow", "Check access"),
                        (
                            "download_allowed",
                            "allowed",
                            "download",
                            "guard",
                            "Recipient can download",
                        ),
                        ("notified", "share", "message", "flow", "Send sharing message"),
                    ]
                ],
            }
        ],
        "decisions": [
            {
                "id": "D_ACCESS",
                "topic": "authority",
                "blocking": True,
                "status": "resolved",
                "source_refs": ["U0"],
                "affects": ["allowed", "download_allowed"],
                "question": "Who may download the file?",
                "why": "The link checks recipient access.",
                "resolution": {
                    "kind": "user_answer",
                    "text": "The selected recipient may download.",
                    "source_refs": ["U0"],
                },
            }
        ],
    }


def requested():
    doc = confirmed()
    doc["sources"].append(
        {
            "id": "U1",
            "kind": "user",
            "text": "我还要能撤回共享。已经发出的下载链接怎么办？",
            "locator": "Synthetic later user request",
        }
    )
    doc["decisions"].append(
        {
            "id": "D_WITHDRAW",
            "topic": "authority",
            "blocking": True,
            "status": "open",
            "source_refs": ["U1"],
            "affects": ["allowed", "download_allowed"],
            "question": "撤回后，已经发出的链接也要停止下载吗？",
            "why": "This changes the existing download condition.",
        }
    )
    return doc


def answered():
    doc = requested()
    doc["sources"].append(
        {
            "id": "U2",
            "kind": "user",
            "text": "是的，撤回以后旧链接的下一次下载也要拒绝。",
            "locator": "Synthetic later user clarification",
        }
    )
    doc["decisions"][-1].update(
        status="resolved",
        resolution={
            "kind": "user_answer",
            "text": "The next download through an old link is rejected after withdrawal.",
            "source_refs": ["U2"],
        },
    )
    doc["networks"][0]["nodes"][2].update(
        label="Recipient with active share", source_refs=["U0", "U2"]
    )
    doc["networks"][0]["edges"][2].update(
        label="Recipient and share still active", source_refs=["U0", "U2"]
    )
    return doc


class IterationDialogueTests(unittest.TestCase):
    def setUp(self):
        (ROOT / ".validation").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".validation")
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_only_the_new_ambiguity_is_asked_and_blocks_confirmation(self):
        result = assess(requested(), previous=confirmed())
        self.assertTrue(result["valid"], result)
        self.assertFalse(result["ready"])
        self.assertEqual(result["blocked"], ["D_WITHDRAW"])
        self.assertEqual([item["id"] for item in result["questions"]], ["D_WITHDRAW"])
        self.assertEqual(requested()["decisions"][0], confirmed()["decisions"][0])

    def test_waiting_question_is_not_repeated_on_the_next_turn(self):
        doc = requested()
        doc["sources"].append(
            {
                "id": "A1",
                "kind": "assistant",
                "text": doc["decisions"][-1]["question"],
                "locator": "Synthetic clarification turn",
            }
        )
        doc["decisions"][-1]["asked_in"] = ["A1"]
        result = assess(doc, previous=confirmed())
        self.assertEqual(result["questions"], [])
        self.assertEqual(result["awaiting_answers"], ["D_WITHDRAW"])
        self.assertFalse(result["ready"])

    def test_user_answer_updates_only_the_existing_local_region(self):
        before, after = confirmed(), answered()
        self.assertTrue(assess(after, previous=before)["ready"])
        old, new = before["networks"][0], after["networks"][0]
        self.assertEqual([n["id"] for n in old["nodes"]], [n["id"] for n in new["nodes"]])
        self.assertEqual([e["id"] for e in old["edges"]], [e["id"] for e in new["edges"]])
        self.assertEqual(old["nodes"][-1], new["nodes"][-1])
        self.assertEqual(old["edges"][-1], new["edges"][-1])
        self.assertEqual(old["nodes"][:2], new["nodes"][:2])
        self.assertEqual(after["decisions"][0], before["decisions"][0])

    def test_actual_local_preview_retains_neighbors_boundaries_and_ids(self):
        write(self.root / "discovery.json", answered())
        result = BODesign(self.root).preview(
            "http://127.0.0.1:8123/graph", ["business.allowed", "business.download"], max_nodes=3
        )
        focus = result["focus"]
        self.assertEqual(
            {n["id"] for n in focus["nodes"]},
            {"business.share", "business.allowed", "business.download"},
        )
        self.assertEqual({e["id"] for e in focus["edges"]}, {"shared", "download_allowed"})
        self.assertEqual({e["edge_id"] for e in focus["boundaries"]}, {"uploaded", "notified"})
        self.assertIn("Recipient and share still active", result["markdown"])
        self.assertEqual(
            json.loads((self.root / "discovery.json").read_text(encoding="utf-8")), answered()
        )

    def test_changed_previous_answer_requires_history_and_actual_change_source(self):
        before, after = confirmed(), confirmed()
        after["sources"].append(
            {
                "id": "U1",
                "kind": "user",
                "text": "Only the owner may download now.",
                "locator": "Synthetic explicit replacement",
            }
        )
        after["decisions"][0]["resolution"] = {
            "kind": "user_answer",
            "text": "Only the owner may download.",
            "source_refs": ["U1"],
        }
        self.assertFalse(assess(after, previous=before)["valid"])
        after["changes"] = [
            {
                "id": "C1",
                "decision": "D_ACCESS",
                "previous": deepcopy(before["decisions"][0]),
                "source_refs": ["U1"],
                "reason": "The user explicitly replaces recipient access.",
            }
        ]
        self.assertTrue(assess(after, previous=before)["ready"])
        after["sources"][-1]["kind"] = "inference"
        self.assertFalse(assess(after, previous=before)["valid"])

    def test_source_only_refactor_reuses_business_confirmation(self):
        doc = confirmed()
        self.assertTrue(assess(doc, previous=deepcopy(doc))["ready"])
        self.assertEqual(assess(doc, previous=deepcopy(doc))["questions"], [])
        write(self.root / "discovery.json", doc)
        first = BODesign(self.root).view()["model"]
        second = BODesign(self.root).view()["model"]
        self.assertEqual(first, second)

    def test_cli_checks_history_and_writes_the_same_focused_graph(self):
        write(self.root / "discovery.json", answered())
        write(self.root / "previous.json", confirmed())
        checked = subprocess.run(
            [
                sys.executable,
                "-B",
                "-X",
                "utf8",
                str(SCRIPTS / "requirements_dialogue.py"),
                "check",
                "--file",
                str(self.root / "discovery.json"),
                "--previous",
                str(self.root / "previous.json"),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=20,
        )
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        preview = subprocess.run(
            [
                sys.executable,
                "-B",
                "-X",
                "utf8",
                str(SCRIPTS / "bo_design.py"),
                "preview",
                "--root",
                str(self.root),
                "--nodes",
                "business.allowed",
                "business.download",
                "--url",
                "http://127.0.0.1:8123/graph",
                "--max-nodes",
                "3",
                "--out",
                "review/preview.md",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=20,
        )
        self.assertEqual(preview.returncode, 0, preview.stdout + preview.stderr)
        saved = json.loads((self.root / "review/preview.json").read_text(encoding="utf-8"))
        self.assertEqual(
            saved["focus"]["selection"]["nodes"], ["business.allowed", "business.download"]
        )
        self.assertIn(
            "Recipient and share still active",
            (self.root / "review/preview.md").read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
