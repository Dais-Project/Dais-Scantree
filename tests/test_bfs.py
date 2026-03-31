from __future__ import annotations

from pathlib import Path
import os

import pytest

from dais_scantree.bfs import scandir_recursive_bfs


def _depth(relpath: str) -> int:
    return len(Path(relpath).parts)


def test_scandir_recursive_bfs_respects_bfs_depth_order(make_tree, scan_relpaths) -> None:
    root = make_tree(
        {
            "a.txt": "",
            "dir1": {
                "b.txt": "",
                "sub": {"c.txt": ""},
            },
            "dir2": {"d.txt": ""},
        }
    )

    relpaths = scan_relpaths(root, include_hidden=True, include_gitignored=True)
    depths = [_depth(path) for path in relpaths]

    assert depths == sorted(depths)
    assert {"a.txt", "dir1", "dir2"}.issubset({p for p in relpaths if _depth(p) == 1})


@pytest.mark.parametrize("scan_limit", [0, -1])
def test_scandir_recursive_bfs_stops_immediately_when_limit_non_positive(make_tree, scan_relpaths, scan_limit: int) -> None:
    root = make_tree({"a.txt": "", "b.txt": ""})

    relpaths = scan_relpaths(root, scan_limit=scan_limit, include_hidden=True, include_gitignored=True)

    assert relpaths == []


def test_scandir_recursive_bfs_applies_scan_limit(make_tree, scan_relpaths) -> None:
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

    relpaths = scan_relpaths(root, scan_limit=2, include_hidden=True, include_gitignored=True)

    assert len(relpaths) == 2


def test_scandir_recursive_bfs_honors_include_hidden(make_tree, scan_relpaths) -> None:
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

    without_hidden = scan_relpaths(root, include_hidden=False, include_gitignored=True)
    with_hidden = scan_relpaths(root, include_hidden=True, include_gitignored=True)

    assert ".hidden.txt" not in without_hidden
    assert ".hidden_dir" not in without_hidden
    assert ".hidden_dir/inside.txt" not in without_hidden
    assert ".hidden.txt" in with_hidden
    assert ".hidden_dir" in with_hidden
    assert ".hidden_dir/inside.txt" in with_hidden


def test_scandir_recursive_bfs_skips_symlinks(make_tree, scan_relpaths) -> None:
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

    relpaths = scan_relpaths(root, include_hidden=True, include_gitignored=True)

    assert "file_link" not in relpaths
    assert "dir_link" not in relpaths
    assert "real_dir" in relpaths
    assert "real_dir/nested.txt" in relpaths


def test_scandir_recursive_bfs_skips_permission_and_missing_directories(monkeypatch, make_tree) -> None:
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

    entries = list(
        scandir_recursive_bfs(
            root,
            scan_limit=100,
            include_hidden=True,
            include_gitignored=True,
        )
    )
    relpaths = [Path(entry.path).resolve().relative_to(root.resolve()).as_posix() for entry in entries]

    assert "ok" in relpaths
    assert "ok/file.txt" in relpaths
    assert "blocked" in relpaths
    assert "blocked/blocked.txt" not in relpaths
    assert "gone" in relpaths
    assert "gone/gone.txt" not in relpaths
