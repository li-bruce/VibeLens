"""Optional observation ports; business execution survives absent observers."""
from contextlib import contextmanager

class NullActivation:
    def result(self, builder):
        return None

class NullProbe:
    @contextmanager
    def span(self, node, builder=lambda: {}, **options):
        yield NullActivation()

    def record(self, *args, **kwargs):
        return None

class NullData:
    def execute(self, node, callback, **kwargs):
        return callback()

    def transaction(self, node, manager, **kwargs):
        return manager

    def transform(self, node, function, value, **kwargs):
        return function(value)

class NullObserver:
    def state(self, *args, **kwargs):
        return None

    def policy(self, *args, **kwargs):
        return None
