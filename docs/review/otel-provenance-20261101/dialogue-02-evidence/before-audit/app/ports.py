"""Failure-isolated observation port; business execution works without a collector."""
from contextlib import contextmanager, nullcontext


class BOResult:
    def result(self, builder):
        pass

    def record(self, phase, builder):
        return None


class BOQuiet:
    @contextmanager
    def span(self, node, builder=lambda: {}, **identity):
        yield BOResult()

    def record(self, node, phase, builder, **identity):
        return None

    def policy(self, declaration, evaluation):
        pass

    def inject(self):
        return {}

    def receive(self, carrier):
        return nullcontext()

    def snapshot(self, rows):
        pass

    def state(self, *args, **kwargs):
        pass

    def data(self, node, callback, **options):
        return callback()

    def transaction(self, node, manager):
        return manager

    def transform(self, node, function, value):
        return function(value)
