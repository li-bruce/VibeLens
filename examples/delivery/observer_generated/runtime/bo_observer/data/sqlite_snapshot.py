"""Reflect immutable SQLite images without holding the publisher's database open.

This path is only for applications that publish a complete, closed database by
atomic file replacement (for example, a sql.js export). Ordinary SQLite writers
and WAL databases need the normal transactional collector. This is not a generic
live-database copy or a backup API.
"""

from contextlib import contextmanager
import os
from pathlib import Path
import sqlite3
import tempfile

MAX_SNAPSHOT_BYTES = 128 * 1024 * 1024


class SnapshotError(ValueError):
    """A snapshot precondition failed; messages contain no paths or row values."""


def file_mode(store):
    """Validate the explicit persistence fact, including direct collector callers."""
    mode = store.get("sqlite_file_mode", "transactional")
    if mode not in ("transactional", "atomic_replace"):
        raise SnapshotError("sqlite_file_mode must be transactional or atomic_replace.")
    if "sqlite_file_mode" in store and store.get("engine") != "sqlalchemy":
        raise SnapshotError("sqlite_file_mode requires a SQLAlchemy SQLite store.")
    return mode


def _open_windows_link(path):
    """Read a private alias and delete that alias when its handle closes.

    Opening the publisher's own path can still block MoveFileEx replacement,
    even with FILE_SHARE_DELETE. The caller therefore creates a separate hard
    link first. DELETE access applies to that alias; file contents are read-only.
    DELETE_ON_CLOSE also releases the link if this process terminates abruptly.
    """
    import ctypes
    from ctypes import wintypes
    import msvcrt

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    create.restype = wintypes.HANDLE
    close = kernel.CloseHandle
    close.argtypes = [wintypes.HANDLE]
    close.restype = wintypes.BOOL
    native_path = str(Path(path).resolve())
    if not native_path.startswith("\\\\?\\"):
        native_path = (
            "\\\\?\\UNC\\" + native_path[2:]
            if native_path.startswith("\\\\")
            else "\\\\?\\" + native_path
        )
    # GENERIC_READ | DELETE; share all; OPEN_EXISTING; sequential + delete-on-close.
    handle = create(native_path, 0x80010000, 0x1 | 0x2 | 0x4, None, 3, 0x0C000080, None)
    if handle == wintypes.HANDLE(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
    except BaseException:
        close(handle)
        raise
    try:
        return os.fdopen(descriptor, "rb")
    except BaseException:
        os.close(descriptor)
        raise


@contextmanager
def open_published_image(path):
    """Pin an atomic publication without opening its replaceable Windows name.

    The temporary directory must be on the database volume and support hard
    links. A failure stays explicit: copying a mutable live database or falling
    back to a blocking handle would violate this collector's contract. Hard
    links add a temporary name, not a copy of the database or its row contents.
    """
    if os.name != "nt":
        with Path(path).open("rb") as stream:
            yield stream
        return
    with tempfile.TemporaryDirectory(prefix="vibelens-sqlite-") as directory:
        alias = Path(directory) / "image.sqlite"
        try:
            os.link(path, alias)
        except OSError:
            raise SnapshotError(
                "Atomic SQLite snapshots require a writable same-volume temporary directory with hard-link support."
            ) from None
        with _open_windows_link(alias) as stream:
            yield stream


def _standalone(path):
    """Conservatively reject sidecars instead of copying an active transaction."""
    if any(Path(str(path) + suffix).exists() for suffix in ("-wal", "-shm", "-journal")):
        raise SnapshotError("Atomic SQLite snapshots require a standalone database image.")


def read_image(path):
    """Read one bounded immutable image, then release the file before reflection.

    A complete image temporarily includes data pages in memory; only Inspector's
    schema metadata leaves this module. The Windows alias is deleted on handle
    close; no database copy or rows are exported. A size/header/mutation failure
    is explicit, never a live fallback.
    """
    _standalone(path)
    with open_published_image(path) as stream:
        before = os.fstat(stream.fileno())
        if not 100 <= before.st_size <= MAX_SNAPSHOT_BYTES:
            raise SnapshotError("Atomic SQLite image exceeds the size limit or is incomplete.")
        image = stream.read(MAX_SNAPSHOT_BYTES + 1)
        after = os.fstat(stream.fileno())
    _standalone(path)
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise SnapshotError("Atomic SQLite image changed in place during collection.")
    if len(image) != before.st_size:
        raise SnapshotError("Atomic SQLite image changed size during collection.")
    if image[:16] != b"SQLite format 3\x00" or image[18:20] != b"\x01\x01":
        raise SnapshotError("Atomic SQLite snapshots require a standalone database image.")
    return image


def create_snapshot_engine(sa, path):
    """Use the existing SQLAlchemy Inspector against an isolated query-only image."""
    if not hasattr(sqlite3.Connection, "deserialize"):
        raise SnapshotError("Atomic SQLite snapshots require sqlite3 deserialize support.")
    image = read_image(path)

    def connect():
        connection = sqlite3.connect(":memory:")
        try:
            connection.deserialize(image)
            connection.execute("PRAGMA query_only = ON")
            return connection
        except BaseException:
            connection.close()
            raise

    return sa.create_engine("sqlite+pysqlite:///:memory:", creator=connect)
