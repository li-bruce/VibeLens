"""Small native SQLite application; no VibeLens imports or graph mutations."""


def share(connection, allowed):
    """Stage one grant change in the application's transaction.

    Args:
        connection: Native SQLite connection owned by the caller.
        allowed: Current permission decision for this invocation.
    """
    if not allowed:
        raise PermissionError("Sharing is not permitted")
    connection.execute("UPDATE states SET value = 'active' WHERE model = 'grant'")


def commit(connection):
    """Commit the actual native transaction; propagate any database exception."""
    connection.commit()


def read_native(connection):
    """Read both independent model values directly from SQLite."""
    return dict(connection.execute("SELECT model, value FROM states"))


def read_commit(statements):
    """Read the native SQLite trace's transaction completions."""
    return "sqlite-commit-" + str(sum(statement == "COMMIT" for statement in statements))


def enqueue(queue, job):
    """Put an immutable job description on the native queue."""
    queue.put(dict(job))


def consume(allowed):
    """Process the permission value received by the worker.

    Args:
        allowed: Permission value carried by this job.
    """
    return allowed


def read_job(job):
    """Independently inspect the received native job, without reading observations."""
    return dict(job)
