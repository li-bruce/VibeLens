"""Read current source bytes without repeatedly resolving ordinary parent paths.

Readers retain ancestor paths only. File contents and current attributes are
always reread; timestamps and file sizes never stand in for source identity.
Symlinks and Windows reparse points use full physical containment checks before
any content is read.
"""

from pathlib import Path
import stat


class SourceFiles:
    """Reuse ancestor path lists while checking their current file attributes."""

    def __init__(self, root):
        self.root = Path(root).absolute().resolve()
        self.parents = {self.root: (self.root,)}

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
