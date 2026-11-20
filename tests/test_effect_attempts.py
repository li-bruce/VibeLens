"""Distinguish observed rollbacks from missing or falsely successful effects."""

from copy import deepcopy
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "skills/vibelens/scripts"), str(ROOT / "tests")]
from test_concept_models import effect_fixture, effect_observations
from bo_observer.concepts.runtime import runtime_errors


def with_aborted_attempt():
    """One actual commit and a separate failed business/transaction invocation."""
    payload = effect_observations()
    events = payload["runs"][0]["events"]
    aborted = deepcopy(events)
    for event in aborted:
        event["id"] += "-abort"
        event["call_id"] += "-abort"
        if event.get("parent_event_id"):
            event["parent_event_id"] += "-abort"
        if "outputs" in event:
            event["outputs"]["transaction_id"] = "tx-abort"
    aborted[-1].update(phase="error", exception={"type": "PermissionError"})
    aborted[-1]["outputs"]["committed"] = False
    aborted.append(
        {
            "id": "share-error",
            "node": "native:share",
            "call_id": "share-1-abort",
            "phase": "error",
            "exception": {"type": "PermissionError"},
        }
    )
    events.extend(aborted)
    return payload


class EffectAttemptTests(unittest.TestCase):
    def errors(self, payload):
        doc, model, _ = effect_fixture()
        return runtime_errors(doc, model, payload)

    def test_native_start_identity_can_be_an_input(self):
        payload = effect_observations()
        entry = payload["runs"][0]["events"][1]
        entry["inputs"] = entry.pop("outputs")
        self.assertEqual(self.errors(payload), [])

    def test_start_identity_directions_must_agree_when_both_exist(self):
        payload = effect_observations()
        payload["runs"][0]["events"][1]["inputs"] = {"transaction_id": "other"}
        self.assertTrue(any("identity differs" in error for error in self.errors(payload)))

    def test_commit_and_failed_attempt_remain_separate(self):
        self.assertEqual(self.errors(with_aborted_attempt()), [])

    def test_only_failed_attempts_do_not_satisfy_a_commit_expectation(self):
        payload = with_aborted_attempt()
        del payload["runs"][0]["events"][:3]
        self.assertTrue(any("completion missing" in error for error in self.errors(payload)))

    def test_abort_cannot_hide_missing_or_false_completion(self):
        mutations = [
            lambda events: events.pop(5),
            lambda events: events.pop(6),
            lambda events: events[6].update(phase="return"),
            lambda events: events[6].update(call_id="another-business-invocation"),
            lambda events: events[6].update(producer_id="another-producer"),
            lambda events: events[5]["outputs"].update(transaction_id="other"),
            lambda events: events[5]["outputs"].update(committed=True),
            lambda events: events.append({**events[5], "id": "duplicate-terminal"}),
            lambda events: events.append(
                {**events[6], "id": "conflicting-owner", "phase": "return"}
            ),
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                payload = with_aborted_attempt()
                mutation(payload["runs"][0]["events"])
                self.assertTrue(self.errors(payload))


if __name__ == "__main__":
    unittest.main()
