"""Optional, non-authoritative observation ports."""


class NullTrace:
    def record(self, *args, **kwargs):
        return None

    def policy(self, *args, **kwargs):
        return None

    def state(self, *args, **kwargs):
        return None


class NullData:
    def execute(self, node, callback, **kwargs):
        return callback()

    def transaction(self, node, manager, **kwargs):
        return manager

    def transform(self, node, function, value, **kwargs):
        return function(value)
