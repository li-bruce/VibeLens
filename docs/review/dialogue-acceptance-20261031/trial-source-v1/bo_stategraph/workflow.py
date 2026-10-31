"""Drive sharing from the canonical machine declaration using the native executor."""

from bo_stategraph.native_executor import BOExecutor


class SharingWorkflow:
    def __init__(self, machine, allowed):
        self.permission = allowed
        self.executor = BOExecutor(machine, {"authorized":self.authorized})

    def authorized(self, context: dict, payload: dict) -> bool:
        return self.permission is True

    def advance(self, state: str, event: str, context: dict) -> dict:
        return self.executor.step(state, event, context, {})
