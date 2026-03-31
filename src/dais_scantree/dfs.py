import os
from collections.abc import Generator
from pathlib import Path
from .ignore_rule import IgnoreRuleNode, is_hidden, load_gitignore_spec


type ScanItem = tuple[os.DirEntry, int]

def scan_with_gitignore(
    root: Path,
    scan_limit: int,
    max_depth: int | None = None,
    include_hidden: bool = False,
) -> Generator[ScanItem, None, None]:
    def gen(node: IgnoreRuleNode, depth: int):
        nonlocal count
        if max_depth is not None and depth > max_depth: return

        try:
            with os.scandir(node.path) as entries:
                for entry in entries:
                    if count >= scan_limit: return
                    if entry.is_symlink(): continue
                    entry_path = Path(entry)
                    if node.check_ignore(entry_path): continue
                    if not include_hidden and is_hidden(entry_path): continue
                    yield entry, depth
                    count += 1
                    if entry.is_dir():
                        child_node = IgnoreRuleNode(entry_path, load_gitignore_spec(entry_path), node)
                        yield from gen(child_node, depth + 1)
        except (PermissionError, FileNotFoundError):
            # Skip inaccessible or deleted directories
            pass

    count = 0
    root_node = IgnoreRuleNode(root, load_gitignore_spec(root))
    yield from gen(root_node, 0)

def scan_without_gitignore(
    root: Path,
    scan_limit: int,
    max_depth: int | None = None,
    include_hidden: bool = False,
) -> Generator[ScanItem, None, None]:
    def gen(dir: Path, depth: int):
        nonlocal count
        if max_depth is not None and depth > max_depth: return

        try:
            with os.scandir(dir) as entries:
                for entry in entries:
                    if count >= scan_limit: return
                    if entry.is_symlink(): continue
                    entry_path = Path(entry)
                    if not include_hidden and is_hidden(entry_path):
                        continue
                    yield entry, depth
                    count += 1
                    if entry.is_dir():
                        yield from gen(entry_path, depth + 1)
        except (PermissionError, FileNotFoundError):
            # Skip inaccessible or deleted directories
            pass

    count = 0
    yield from gen(root, 0)

def scan(
    directory: str | Path,
    scan_limit: int,
    max_depth: int | None = None,
    include_hidden: bool = False,
    include_gitignored: bool = False,
) -> Generator[ScanItem, None, None]:
    """
    Depth-first recursive scan (pre-order).

    if scan_limit is less than or equal to 0, the scan will stop immediately and yield nothing.
    if max_depth is not None, the scan will stop when the depth exceeds max_depth.

    Yields:
        os.DirEntry objects for all items (both files and directories) in the directory tree, in DFS pre-order.
    """
    root = Path(directory).resolve()

    if include_gitignored:
        yield from scan_without_gitignore(root, scan_limit, max_depth, include_hidden)
    else:
        yield from scan_with_gitignore(root, scan_limit, max_depth, include_hidden)
