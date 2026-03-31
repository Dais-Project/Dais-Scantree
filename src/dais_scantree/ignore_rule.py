import pathspec
from typing import Callable
from pathlib import Path


class IgnoreRuleNode:
    def __init__(self,
                 path: Path,
                 spec: pathspec.PathSpec | None = None,
                 parent: IgnoreRuleNode | None = None
                 ):
        self.path = path
        self.spec = spec
        self.parent: IgnoreRuleNode | None = parent

    @staticmethod
    def _check_ignore_by_spec(spec: pathspec.PathSpec, path: str) -> bool | None:
        ignored: bool | None = None
        for pattern in spec.patterns:
            if pattern.include is None:
                continue
            if pattern.match_file(path):
                ignored = pattern.include
        return ignored

    def check_ignore(self, path: Path) -> bool:
        node = self
        while node is not None:
            if node.spec is None:
                node = node.parent
                continue

            try:
                rel_path = path.relative_to(node.path).as_posix()
                if path.is_dir(): rel_path += "/"
            except ValueError:
                node = node.parent
                continue

            if (ignore := self._check_ignore_by_spec(node.spec, rel_path)) is not None:
                return ignore
            node = node.parent
        return False

def load_gitignore_spec(cwd: Path) -> pathspec.PathSpec | None:
    gitignore_path = cwd / ".gitignore"
    if gitignore_path.exists():
        with open(gitignore_path, "r", encoding="utf-8") as f:
            return pathspec.PathSpec.from_lines("gitignore", f)
    return None

is_hidden: Callable[[Path], bool] = lambda path: path.name.startswith(".")
