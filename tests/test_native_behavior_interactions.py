"""Cross-model witnesses require causality as well as equal selected values."""

from copy import deepcopy
import unittest

import test_behavior_contract  # Add the maintained observer package to sys.path.
from bo_observer.behavior.native_interactions import boundary_errors


def record(role, ident, values, *, parents=(), action=None):
    return {"role": role, "action": action or role, "values": values,
            "event": {"id": ident, "node": role, "phase": "read",
                      "depends": [{"event": parent, "type": "trigger"} for parent in parents]}}


class InteractionBoundaryTests(unittest.TestCase):
    def check(self, interaction, records):
        return boundary_errors(interaction, records, [r["event"] for r in records])

    def test_equal_payloads_do_not_establish_handoff(self):
        values = {"correlation": "job-1", "payload": {"file": "f"}}
        send = record("send", "s", values)
        receive = record("receive", "r", deepcopy(values))
        interaction = {"kind": "handoff"}
        self.assertEqual(self.check(interaction, [send, receive])[0]["code"], "handoff_send_unwitnessed")
        receive["event"]["depends"] = [{"event": "s", "type": "trigger"}]
        self.assertEqual(self.check(interaction, [receive, send]), [])
        receive["values"]["payload"]["file"] = "other"
        self.assertTrue(self.check(interaction, [send, receive]))

    def test_acknowledgement_needs_the_actual_receive(self):
        send = record("send", "s", {"correlation": "j", "payload": 1})
        receive = record("receive", "r", {"correlation": "j", "payload": 1}, parents=["s"])
        ack = record("acknowledge", "a", {"correlation": "j"}, parents=["r"])
        self.assertEqual(self.check({"kind": "handoff"}, [send, receive, ack]), [])
        ack["event"]["depends"] = [{"event": "s", "type": "trigger"}]
        self.assertTrue(self.check({"kind": "handoff"}, [send, receive, ack]))

    def test_resource_release_keeps_holder_and_acquisition_identity(self):
        values = {"resource": "worker", "holder": "job1", "operation": "acquire1"}
        acquired = record("acquire", "a", values)
        released = record("release", "r", deepcopy(values), parents=["a"])
        self.assertEqual(self.check({"kind": "resource"}, [acquired]), [])
        self.assertEqual(self.check({"kind": "resource"}, [acquired, released]), [])
        repeated = deepcopy(released)
        repeated["event"]["id"] = "r2"
        self.assertTrue(self.check({"kind": "resource"}, [acquired, released, repeated]))
        released["values"]["holder"] = "other"
        self.assertTrue(self.check({"kind": "resource"}, [acquired, released]))

    def test_join_requires_every_observed_member(self):
        one = record("arrive", "1", {"correlation": "j", "member": "scan"})
        two = record("arrive", "2", {"correlation": "j", "member": "review"})
        joined = record("join", "3", {"correlation": "j", "members": ["scan", "review"]}, parents=["1", "2"])
        self.assertEqual(self.check({"kind": "join"}, [one, two, joined]), [])
        joined["event"]["depends"].pop()
        self.assertTrue(self.check({"kind": "join"}, [one, two, joined]))

    def test_transaction_does_not_infer_commit_from_member_return(self):
        write = record("member", "w", {"transaction": "t"}, action="write")
        member = record("member", "c", {"transaction": "t"}, action="save", parents=["w"])
        commit = record("commit", "c", {"transaction": "t"}, action="save", parents=["w"])
        interaction = {"kind": "transaction", "member_actions": ["write", "save"]}
        self.assertEqual(self.check(interaction, [write, member, commit]), [])
        commit["values"]["transaction"] = "other"
        self.assertTrue(self.check(interaction, [write, member, commit]))

    def test_joint_read_uses_explicit_snapshot_groups(self):
        a = record("read", "a", {"group": "joint1", "revision": 1, "value": "active"}, action="a")
        b = record("read", "b", deepcopy(a["values"]), action="b")
        interaction = {"kind": "shared_read", "consistency": "revision", "reader_actions": ["a", "b"]}
        self.assertEqual(self.check(interaction, [a, b]), [])
        b["values"]["revision"] = 2
        self.assertTrue(self.check(interaction, [a, b]))
        interaction["consistency"] = "independent"
        self.assertEqual(self.check(interaction, [a, b]), [])


if __name__ == "__main__":
    unittest.main()
