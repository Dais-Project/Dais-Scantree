from __future__ import annotations

import os
from pathlib import Path

import pytest
from dais_scantree import dfs as scantree_dfs


def _entries_to_relpaths_with_depth(entries: list[tuple[os.DirEntry[str], int]], root: Path) -> list[tuple[str, int]]:
    resolved_root = root.resolve()
    return [
        (Path(entry.path).resolve().relative_to(resolved_root).as_posix(), depth)
        for entry, depth in entries
    ]

def _scan_relpaths_with_depth(
    root: Path,
    *,
    scan_limit: int = 10_000,
    max_depth: int | None = None,
    include_hidden: bool = False,
    include_gitignored: bool = False,
) -> list[tuple[str, int]]:
    entries = list(
        scantree_dfs(
            root,
            scan_limit=scan_limit,
            max_depth=max_depth,
            include_hidden=include_hidden,
            include_gitignored=include_gitignored,
        )
    )
    return _entries_to_relpaths_with_depth(entries, root)

def _scan_relpaths(
    root: Path,
    *,
    scan_limit: int = 10_000,
    max_depth: int | None = None,
    include_hidden: bool = False,
    include_gitignored: bool = False,
) -> list[str]:
    return [
        relpath
        for relpath, _ in _scan_relpaths_with_depth(
            root,
            scan_limit=scan_limit,
            max_depth=max_depth,
            include_hidden=include_hidden,
            include_gitignored=include_gitignored,
        )
    ]

def test_scandir_recursive_dfs_respects_depth_first_preorder(make_tree) -> None:
    root = make_tree(
        {
            "dir": {
                "sub1": {"deep.txt": ""},
                "sub2": {"leaf.txt": ""},
            }
        }
    )

    relpaths = _scan_relpaths(root, include_hidden=True, include_gitignored=True)
    indices = {path: idx for idx, path in enumerate(relpaths)}

    assert "dir" in indices
    assert "dir/sub1" in indices
    assert "dir/sub2" in indices
    assert "dir/sub1/deep.txt" in indices
    assert "dir/sub2/leaf.txt" in indices

    assert indices["dir"] < indices["dir/sub1"]
    assert indices["dir"] < indices["dir/sub2"]

    if indices["dir/sub1"] < indices["dir/sub2"]:
        assert indices["dir/sub1/deep.txt"] < indices["dir/sub2"]
    else:
        assert indices["dir/sub2/leaf.txt"] < indices["dir/sub1"]

@pytest.mark.parametrize("scan_limit", [0, -1])
def test_scandir_recursive_dfs_stops_immediately_when_limit_non_positive(make_tree, scan_limit: int) -> None:
    root = make_tree({"a.txt": "", "b.txt": ""})
    relpaths = _scan_relpaths(root, scan_limit=scan_limit, include_hidden=True, include_gitignored=True)
    assert relpaths == []

def test_scandir_recursive_dfs_applies_scan_limit(make_tree) -> None:
    root = make_tree(
        {
            "a.txt": "",
            "b.txt": "",
            "dir": {
                "c.txt": "",
                "d.txt": "",
            },
        }
    )

    relpaths = _scan_relpaths(root, scan_limit=2, include_hidden=True, include_gitignored=True)
    assert len(relpaths) == 2

def test_scandir_recursive_dfs_honors_include_hidden(make_tree) -> None:
    root = make_tree(
        {
            "visible.txt": "",
            ".hidden.txt": "",
            "sub": {
                "visible2.txt": "",
                ".deep_hidden.txt": "",
            },
            ".hidden_dir": {
                "inside.txt": "",
            },
        }
    )

    without_hidden = _scan_relpaths(root, include_hidden=False, include_gitignored=True)
    with_hidden = _scan_relpaths(root, include_hidden=True, include_gitignored=True)

    assert ".hidden.txt" not in without_hidden
    assert ".hidden_dir" not in without_hidden
    assert ".hidden_dir/inside.txt" not in without_hidden
    assert ".hidden.txt" in with_hidden
    assert ".hidden_dir" in with_hidden
    assert ".hidden_dir/inside.txt" in with_hidden


def test_scandir_recursive_dfs_skips_symlinks(make_tree) -> None:
    root = make_tree(
        {
            "target.txt": "target",
            "real_dir": {
                "nested.txt": "nested",
            },
        }
    )

    file_link = root / "file_link"
    dir_link = root / "dir_link"

    try:
        file_link.symlink_to(root / "target.txt")
        dir_link.symlink_to(root / "real_dir", target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("当前环境不支持创建符号链接")

    relpaths = _scan_relpaths(root, include_hidden=True, include_gitignored=True)

    assert "file_link" not in relpaths
    assert "dir_link" not in relpaths
    assert "real_dir" in relpaths
    assert "real_dir/nested.txt" in relpaths

def test_scandir_recursive_dfs_skips_permission_and_missing_directories(monkeypatch, make_tree) -> None:
    root = make_tree(
        {
            "ok": {"file.txt": ""},
            "blocked": {"blocked.txt": ""},
            "gone": {"gone.txt": ""},
        }
    )

    blocked = (root / "blocked").resolve()
    gone = (root / "gone").resolve()
    original_scandir = os.scandir

    def fake_scandir(path):
        resolved = Path(path).resolve()
        if resolved == blocked:
            raise PermissionError("blocked")
        if resolved == gone:
            raise FileNotFoundError("gone")
        return original_scandir(path)

    monkeypatch.setattr(os, "scandir", fake_scandir)

    relpaths = _scan_relpaths(root, scan_limit=100, include_hidden=True, include_gitignored=True)

    assert "ok" in relpaths
    assert "ok/file.txt" in relpaths
    assert "blocked" in relpaths
    assert "blocked/blocked.txt" not in relpaths
    assert "gone" in relpaths
    assert "gone/gone.txt" not in relpaths

def test_scandir_recursive_dfs_honors_max_depth(make_tree) -> None:
    root = make_tree(
        {
            "lv1_file.txt": "",
            "lv1_dir": {
                "lv2_file.txt": "",
                "lv2_dir": {
                    "lv3_file.txt": "",
                },
            },
        }
    )

    relpaths_with_depth = _scan_relpaths_with_depth(
        root,
        max_depth=2,
        include_hidden=True,
        include_gitignored=True,
    )
    relpaths = [path for path, _ in relpaths_with_depth]

    assert "lv1_file.txt" in relpaths
    assert "lv1_dir" in relpaths
    assert "lv1_dir/lv2_file.txt" in relpaths
    assert "lv1_dir/lv2_dir" in relpaths
    assert "lv1_dir/lv2_dir/lv3_file.txt" not in relpaths
    assert all(depth <= 2 for _, depth in relpaths_with_depth)
