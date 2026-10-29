"""The review exporter must never include reasoning or arbitrary tool output."""

import importlib.util
from pathlib import Path
import json
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "trial_export",
    Path(__file__).resolve().parents[1] / "tools/export_trial_dialogue.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ExportTests(unittest.TestCase):
    def message(self, role, phase, text):
        return {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": role,
                "phase": phase,
                "content": [{"type": "output_text", "text": text}],
            },
        }

    def test_only_visible_assistant_phases(self):
        self.assertIsNone(module.public_record(self.message("assistant", "analysis", "private")))
        self.assertIsNone(module.public_record(self.message("developer", None, "private")))
        self.assertEqual(
            module.public_record(self.message("assistant", "commentary", "visible"))["text"],
            "visible",
        )

    def test_delivered_prompt_not_arbitrary_tool_output(self):
        record = {
            "type": "response_item",
            "payload": {
                "type": "function_call_output",
                "name": "send_message_to_thread",
                "output": "<codex_delegation><input>Confirm this flow</input></codex_delegation>",
            },
        }
        self.assertEqual(module.public_record(record)["role"], "scripted-user")
        record["payload"]["name"] = "exec_command"
        self.assertIsNone(module.public_record(record))

    def test_reasoning_is_excluded(self):
        self.assertIsNone(
            module.public_record(
                {
                    "type": "response_item",
                    "payload": {"type": "reasoning", "text": "private"},
                }
            )
        )

    def test_export_preserves_cost_phase_without_exporting_private_context(self):
        root = Path(__file__).resolve().parents[1] / ".validation"
        root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            path = Path(folder) / "trial.jsonl"
            records = [
                {
                    "type": "turn_context",
                    "payload": {
                        "turn_id": "initial",
                        "model": "example",
                        "effort": "high",
                        "instructions": "PRIVATE",
                    },
                },
                self.message("assistant", "analysis", "PRIVATE"),
                self.message("assistant", "final_answer", "Flow confirmed"),
                {
                    "type": "event_msg",
                    "payload": {
                        "type": "token_count",
                        "info": {
                            "total_token_usage": {
                                "input_tokens": 100,
                                "cached_input_tokens": 75,
                                "output_tokens": 20,
                            }
                        },
                    },
                },
                {
                    "type": "turn_context",
                    "payload": {
                        "turn_id": "repair",
                        "model": "example",
                        "effort": "high",
                    },
                },
                {
                    "type": "event_msg",
                    "payload": {
                        "type": "token_count",
                        "info": {
                            "total_token_usage": {
                                "input_tokens": 150,
                                "cached_input_tokens": 110,
                                "output_tokens": 30,
                            }
                        },
                    },
                },
            ]
            path.write_text("\n".join(json.dumps(value) for value in records), encoding="utf-8")
            module.export([path], Path(folder) / "out", "Scoped trial")
            text = (Path(folder) / "out/dialogue.json").read_text(encoding="utf-8")
            self.assertNotIn("PRIVATE", text)
            result = json.loads(text)
            self.assertEqual(
                [item["turn_id"] for item in result["counters"]], ["initial", "repair"]
            )
            self.assertEqual(result["counters"][-1]["usage"]["output_tokens"], 30)

    def test_local_links_stay_readable_without_dead_repository_links(self):
        text = "[Report](WORKSPACE/trial/review.md) ![Screen](<WORKSPACE/trial/screen.png>)"
        rendered = module.readable_text(text)
        self.assertIn("Report (`WORKSPACE/trial/review.md`)", rendered)
        self.assertIn("Screen (`WORKSPACE/trial/screen.png`)", rendered)
        self.assertEqual(
            module.readable_text("[Web](https://example.com)"),
            "[Web](https://example.com)",
        )


if __name__ == "__main__":
    unittest.main()
