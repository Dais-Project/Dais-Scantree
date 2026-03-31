import os
from collections import deque
from collections.abc import Generator
from pathlib import Path
from .ignore_rule import IgnoreRuleNode, load_gitignore_spec, is_hidden


type ScanItem = os.DirEntry

def scan_with_gitignore(root: Path, scan_limit: int, include_hidden: bool = False) -> Generator[ScanItem, None, None]:
    node_queue: deque[IgnoreRuleNode] = deque([IgnoreRuleNode(root, load_gitignore_spec(root))])
    count = 0

    while len(node_queue) > 0:
        node = node_queue.popleft()
        try:
            with os.scandir(node.path) as entries:
                for entry in entries:
                    if count >= scan_limit: return
                    entry_path = Path(entry)
                    if node.check_ignore(entry_path): continue
                    if not include_hidden and is_hidden(entry_path):
                        continue
                    if entry.is_dir():
                        new_node = IgnoreRuleNode(entry_path, load_gitignore_spec(entry_path), node)
                        node_queue.append(new_node)
                    count += 1
                    yield entry
        except (PermissionError, FileNotFoundError):
            # Skip inaccessible or deleted directories
            continue

def scan_without_gitignore(root: Path, scan_limit: int, include_hidden: bool = False) -> Generator[ScanItem, None, None]:
    queue: deque[Path] = deque([root])
    count = 0

    while len(queue) > 0:
        current_dir = queue.popleft()
        try:
            with os.scandir(current_dir) as entries:
                for entry in entries:
                    if count >= scan_limit: return
                    entry_path = Path(entry)
                    if not include_hidden and is_hidden(entry_path):
                        continue
                    if entry.is_dir():
                        queue.append(entry_path)
                    count += 1
                    yield entry
        except (PermissionError, FileNotFoundError):
            # Skip inaccessible or deleted directories
            continue

def scan(
    directory: str | Path,
    scan_limit: int,
    include_hidden: bool = False,
    include_gitignored: bool = False,
) -> Generator[ScanItem, None, None]:
    """
    Breadth-first recursive scan.

    if scan_limit is less than or equal to 0, the scan will stop immediately and yield nothing.

    Yields:
        os.DirEntry objects for all items in the directory tree, in BFS order.
    """
    root = Path(directory).resolve()

    if include_gitignored:
        yield from scan_without_gitignore(root, scan_limit, include_hidden)
    else:
        yield from scan_with_gitignore(root, scan_limit, include_hidden)
