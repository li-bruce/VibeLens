"""Read Windows source through the same handle whose containment was checked.

Checking every ancestor before opening a path repeats filesystem calls and still
leaves a rename/reparse race. GetFinalPathNameByHandleW resolves the opened object,
including junctions; verification and the byte read then refer to that object.
"""

from functools import lru_cache
import os
from pathlib import PureWindowsPath
import stat


@lru_cache(maxsize=1)
def _final_path_api():
    """Load the OS function once; never cache paths, handles or file contents."""
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    function = kernel.GetFinalPathNameByHandleW
    function.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD]
    function.restype = wintypes.DWORD
    return function


def _handle_path(handle):
    """Return the normalized NT path, without querying the DOS mount manager.

    AppContainer processes can read their source but cannot necessarily query
    drive-letter mappings. Both endpoints use the same NT namespace, preserving
    containment without falling back to an unchecked alias or relaxing access.
    """
    import ctypes

    function = _final_path_api()
    capacity = 512
    while capacity <= 32768:
        buffer = ctypes.create_unicode_buffer(capacity)
        # FILE_NAME_NORMALIZED | VOLUME_NAME_NT: resolve reparse targets, retain
        # the device name, and avoid the DOS drive-letter translation entirely.
        length = function(handle, buffer, capacity, 2)
        if not length:
            raise ctypes.WinError(ctypes.get_last_error())
        if length < capacity:
            return PureWindowsPath(buffer.value)
        capacity = length + 1
    raise OSError("Normalized source path exceeds the Windows path limit")


def root_path(root):
    """Resolve the project directory once per source-reading pass, then close it."""
    import ctypes
    from ctypes import wintypes

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
    # FILE_READ_ATTRIBUTES, all share modes, OPEN_EXISTING, BACKUP_SEMANTICS.
    handle = create(str(root), 0x80, 7, None, 3, 0x02000000, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return _handle_path(handle)
    finally:
        close(handle)


def read_contained(root, target):
    """Read fresh bytes from a regular, physically contained file handle.

    A path/ancestor can change before open; the handle still resolves to the
    object we will read. No fallback reads the unchecked path if resolution
    fails. A later rename cannot redirect this already open descriptor.
    """
    import msvcrt

    with target.open("rb") as stream:
        descriptor = stream.fileno()
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            return None
        if not _handle_path(msvcrt.get_osfhandle(descriptor)).is_relative_to(root):
            raise ValueError("path escapes project")
        return stream.read()
