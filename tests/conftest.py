from __future__ import annotations

import os
from pathlib import Path

import pytest
from dais_scantree import bfs as scantree_bfs


type TreeNode = dict[str, TreeNode] | str | None

def build_tree(root: Path, spec: dict[str, TreeNode]) -> None:
    for name, node in spec.items():
        current = root / name
        if isinstance(node, dict):
            current.mkdir(parents=True, exist_ok=True)
            build_tree(current, node)
            continue

        current.parent.mkdir(parents=True, exist_ok=True)
        current.write_text("" if node is None else node, encoding="utf-8")


def entries_to_relpaths(entries: list[os.DirEntry[str]], root: Path) -> list[str]:
    resolved_root = root.resolve()
    return [Path(entry.path).resolve().relative_to(resolved_root).as_posix() for entry in entries]


@pytest.fixture
def make_tree(tmp_path: Path):
    def _make(spec: dict[str, TreeNode]) -> Path:
        build_tree(tmp_path, spec)
        return tmp_path

    return _make


@pytest.fixture
def scan_relpaths():
    def _scan(
        root: Path,
        *,
        scan_limit: int = 10_000,
        include_hidden: bool = False,
        include_gitignored: bool = False,
    ) -> list[str]:
        entries = list(
            scantree_bfs(
                root,
                scan_limit=scan_limit,
                include_hidden=include_hidden,
                include_gitignored=include_gitignored,
            )
        )
        return entries_to_relpaths(entries, root)

    return _scan
