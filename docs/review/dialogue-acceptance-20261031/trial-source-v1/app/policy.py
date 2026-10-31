"""Native authorization evaluates the current declared rule network once per operation."""

from bo_stategraph.native_policy.runtime import evaluate


def flag_enabled(value: bool) -> bool:
    return value is True


def authorize(declaration, operation, facts, revision, root):
    return evaluate(declaration, operation, facts, {"flag_enabled":flag_enabled}, fact_revision=revision, source_root=root)
