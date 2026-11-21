"""Read current source bytes without repeatedly resolving ordinary parent paths.

File contents are always reread; timestamps and file sizes never stand in for
source identity. Windows verifies the actual opened handle before reading it.
Other platforms retain ancestor paths only and check physical containment for
links before reading any content.
"""

from pathlib import Path
import os
import stat


class SourceFiles:
    """Reuse ancestor path lists while checking their current file attributes."""

    def __init__(self, root):
        self.root = Path(root).absolute().resolve()
        self.parents = {self.root: (self.root,)}
        self._windows_root = None

    @staticmethod
    def linked(info):
        """Recognize Unix links and Windows directory/file reparse points."""
        return stat.S_ISLNK(info.st_mode) or bool(
            getattr(info, "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        )

    def plain_parent(self, path):
        if not path.is_relative_to(self.root):
            return False
        if path not in self.parents:
            self.ancestors(path)
        # Cache path construction only. A directory can be replaced by a link
        # between two reads in the same pass, so old attributes are not evidence.
        for parent in self.parents[path]:
            info = parent.lstat()
            if not stat.S_ISDIR(info.st_mode) or self.linked(info):
                return False
        return True

    def ancestors(self, path):
        """Construct relative ancestor lists without resolving every root component."""
        if path not in self.parents:
            self.parents[path] = self.ancestors(path.parent) + (path,)
        return self.parents[path]

    def read(self, name):
        """Return current bytes, or None for an absent/unreadable regular file."""
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("expected contained relative path")
        target = self.root / relative
        try:
            if os.name == "nt":
                from .windows_source import read_contained, root_path

                if self._windows_root is None:
                    self._windows_root = root_path(self.root)
                return read_contained(self._windows_root, target)
            info = target.lstat()
            if self.linked(info) or not self.plain_parent(target.parent):
                target = target.resolve()
                if not target.is_relative_to(self.root):
                    raise ValueError("path escapes project")
                if not target.is_file():
                    return None
            elif not stat.S_ISREG(info.st_mode):
                return None
            return target.read_bytes()
        except OSError:
            return None

    def read_all(self, names):
        """Read every current file in the caller's observation context.

        Admission holds a short consistency boundary. Dispatching these small
        reads to a shared thread pool makes that boundary wait for worker
        scheduling while the live viewer also processes Python data. Sequential
        reads avoid that contention and retain the same byte and containment
        checks, including edits with unchanged size or modification time.
        """
        return {name: self.read(name) for name in names}
