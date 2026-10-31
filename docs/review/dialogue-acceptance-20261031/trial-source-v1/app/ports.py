"""Neutral monitoring port; the application works without observation code."""

from contextlib import contextmanager


class NullActivation:
    def result(self, builder):
        pass

    def record(self, phase, builder):
        return None


class NullMonitor:
    @contextmanager
    def operation(self, node, phase, builder=lambda: {}, **options):
        yield NullActivation()

    @contextmanager
    def span(self, node, builder=lambda: {}, **options):
        yield NullActivation()

    def record(self, node, phase, builder, **options):
        return None

    def policy(self, declaration, evaluation, entity, attempt):
        pass

    def state(self, node, row, result, initial=False):
        pass

    def execute(self, node, callback, **options):
        return callback()

    def transaction(self, node, manager, **options):
        return manager

    def transform(self, node, function, value, **options):
        return function(value)

    def flush(self):
        return True
