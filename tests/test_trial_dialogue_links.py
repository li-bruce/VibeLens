"""Public dialogue evidence stays readable, portable and separate from private items."""

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from export_trial_dialogue import export, readable_text


class TrialDialogueExportTests(unittest.TestCase):
    def test_windows_and_normalized_workspace_links_become_readable_path_text(self):
        for link in (
            "[Review](/WORKSPACE/review/handoff.json)",
            "[Review](WORKSPACE/review/handoff.json)",
            "[Review](/C:/trial/review/handoff.json)",
            "[Review](<C:/trial folder/review/handoff.json>)",
        ):
            with self.subTest(link=link):
                result = readable_text(link)
                self.assertTrue(result.startswith("Review (`"))
                self.assertNotIn("](", result)
                self.assertIn("review/handoff.json", result)

    def test_relative_and_web_links_are_preserved(self):
        text = "[Guide](guide.md) and [Source](https://example.org/source)"
        self.assertEqual(readable_text(text), text)

    def test_export_preserves_public_source_and_excludes_private_items(self):
        public = "Read [Review](/C:/trial/review/handoff.json)"
        rows = [
            {
                "timestamp": "2026-10-31T00:00:00Z",
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "assistant",
                    "phase": "commentary",
                    "content": [{"type": "output_text", "text": public}],
                },
            },
            {
                "type": "response_item",
                "payload": {"type": "reasoning", "text": "private reasoning"},
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "system",
                    "content": [{"type": "text", "text": "private system"}],
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "function_call_output",
                    "name": "exec_command",
                    "output": "private output",
                },
            },
        ]
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as directory:
            base = Path(directory)
            session = base / "session.jsonl"
            session.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
            result = export([session], base / "out", "Visible trial", [("C:/trial", "WORKSPACE")])
            self.assertEqual(result["messages"], 1)
            report = json.loads((base / "out/dialogue.json").read_text(encoding="utf-8"))
            self.assertEqual(report["dialogue"][0]["text"], public.replace("C:/trial", "WORKSPACE"))
            markdown = (base / "out/dialogue.md").read_text(encoding="utf-8")
            self.assertIn("Review (`/WORKSPACE/review/handoff.json`)", markdown)
            self.assertNotIn("](/WORKSPACE", markdown)
            self.assertNotIn("private", markdown)


if __name__ == "__main__":
    unittest.main()
