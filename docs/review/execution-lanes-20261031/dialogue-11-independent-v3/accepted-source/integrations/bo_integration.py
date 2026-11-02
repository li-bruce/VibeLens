"""Optional capture of native business results through the canonical protocol."""
import json
from bo_observer.service import GraphSession
from bo_observer.adapters.python.bo_probe import BOProbe
from bo_observer.data.runtime import BODataRuntime
from bo_observer.policy.recording import record_evaluation
from bo_stategraph.workflow import file_context, machine_snapshot


class BOIntegration:
    def __init__(self, root, mode="on", capacity=8192):
        self.session = GraphSession(root)
        self.evaluations = []
        self.bo_errors = 0
        sink = self.session.bo_sink if mode != "fault" else self.bo_fault
        self.probe = BOProbe(self.session.project, self.session.manifest["build_id"],
            enabled=mode != "off", sink=sink, capacity=capacity)
        config = json.loads((root / "bo_stategraph/databases.json").read_text(encoding="utf-8-sig"))
        self.data = BODataRuntime(self.probe, config)
        self.session.bo_bind_capture(scope_setter=self.probe.bo_set_scope,
            flush_capture=lambda: self.probe.flush(30), health=self.health)

    def bo_fault(self, value, kind):
        raise ConnectionError("Deliberately unavailable observation transport")

    def policy(self, report, entity):
        try:
            self.evaluations.append(report)
            record_evaluation(self.session.model["policy"], report, self.probe,
                entity=entity, attempt=entity, basis={"param_version": 1})
        except Exception:
            self.bo_errors += 1

    def state(self, row, node, transition):
        try:
            evidence = self.probe.record(node, "change", lambda: {"outputs": {
                "file_id": row["id"], "state": row["state"], "revision": row["revision"],
                "recipient_id": row["recipient_id"]}}, entity=row["id"], attempt=row["id"],
                scope="entity", revision=row["revision"], basis={"param_version": 1})
            if evidence:
                configuration = machine_snapshot([row], self.session.manifest["build_id"])["configurations"][0]
                self.probe.snapshot(row["id"], row["state"], file_context(row), row["revision"],
                    evidence, event=transition["event"], guards=transition["guards"],
                    payload=transition["payload"], configuration=configuration)
        except Exception:
            self.bo_errors += 1

    def health(self):
        return {**self.probe.bo_health(), "data_errors": self.data.bo_errors,
            "integration_errors": self.bo_errors}

    def close(self):
        self.probe.flush(30)
        self.probe.close()
        self.data.close()
        self.session.close()
